"""Logical DDQN minibatches with safe microbatches and semantic legal targets."""
from functools import lru_cache
import torch
from torch.nn import functional as F
from videochess_rl.rl.training import DoubleDqnLearner, _batch
from videochess_rl.model.features import replay_observation_history, encode_board
from videochess_rl.model.training import _bounded_index_batches


@lru_cache(maxsize=32768)
def features(history):
    return encode_board(replay_observation_history(history),split='replay')


class ImprovementLearner(DoubleDqnLearner):
    def update(self,*,batch_size=32,gamma=.99):
        batch_size=self.batch_size;gamma=self.gamma
        if len(self.replay)<max(batch_size,self.replay_warmup):return None
        rows=self.replay.sample(batch_size)
        current=tuple(features(r.history_before) for r in rows)
        targets=torch.tensor([r.reward for r in rows],dtype=torch.float32,device=self.device)
        bootstrap=[i for i,r in enumerate(rows) if not r.terminated]
        if bootstrap:
            next_rows=tuple(features(rows[i].history_after) for i in bootstrap)
            with torch.no_grad():
                for ids in _bounded_index_batches(next_rows,range(len(next_rows)),32):
                    next_features=tuple(next_rows[i] for i in ids)
                    inputs=_batch(next_features,self.device)
                    online=self.online(**inputs).masked_fill(~inputs['candidate_mask'],-torch.inf)
                    target=self.target(**inputs)
                    selected=online.argmax(dim=1)
                    values=target.gather(1,selected[:,None]).squeeze(1)
                    if not torch.isfinite(values).all():raise FloatingPointError('nonfinite bootstrap')
                    for k,j in enumerate(ids):
                        row_index=bootstrap[j]
                        if next_features[k].candidate_uci!=rows[row_index].next_legal_actions:raise ValueError('bootstrap semantic UCI mismatch')
                        targets[row_index]+=gamma*values[k]
        self.optimizer.zero_grad(set_to_none=True)
        total=0.
        for ids in _bounded_index_batches(current,range(len(current)),32):
            inputs=_batch(tuple(current[i] for i in ids),self.device)
            scores=self.online(**inputs)
            actions=torch.tensor([current[i].candidate_uci.index(rows[i].selected_uci) for i in ids],device=self.device)
            selected=scores.gather(1,actions[:,None]).squeeze(1)
            loss=F.smooth_l1_loss(selected,targets[ids],reduction='sum')/len(rows)
            if not torch.isfinite(loss):raise FloatingPointError('nonfinite Huber loss')
            loss.backward();total+=loss.item()
        norm=torch.nn.utils.clip_grad_norm_(self.online.parameters(),self.gradient_clip_norm)
        if not torch.isfinite(norm) or any(p.grad is not None and not torch.isfinite(p.grad).all() for p in self.online.parameters()):raise FloatingPointError('nonfinite DDQN gradient')
        self.optimizer.step()
        if any(not torch.isfinite(p).all() for p in self.online.parameters()):raise FloatingPointError('nonfinite DDQN parameters')
        self.optimizer_updates+=1
        synced=self.optimizer_updates%self.target_sync_interval==0
        if synced:
            self.target.load_state_dict(self.online.state_dict());self.target.eval();self.target_syncs+=1
        return dict(loss=total,grad_norm=float(norm),update=self.optimizer_updates,target_sync=int(synced))
