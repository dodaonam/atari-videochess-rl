import hashlib
import os
import unittest
from pathlib import Path
from unittest.mock import patch
import torch
from videochess_rl.model.checkpoint import load_checkpoint, verify_artifact_manifest
from videochess_rl.rl.network import make_warm_scorer, make_scratch_scorer, clone_target
from videochess_rl.rl.cli import (_compatible_initialization_metadata, RECOVERY_COMPATIBLE_CODE_SHA256,
                                  _configured_directory, M4_DIR, M4_CHECKPOINT_SHA)

M4=M4_DIR
EXPECTED=M4_CHECKPOINT_SHA


class InitializationTests(unittest.TestCase):
    def test_private_artifact_directories_are_overridable_without_weakening_hash_checks(self):
        with patch.dict(os.environ, {"VIDEOCHESS_M5_M4_DIR": "~/private/m4",
                                     "VIDEOCHESS_M5_M3_RELEASE_DIR": "/data/private/m3-r6"}):
            self.assertEqual(_configured_directory("VIDEOCHESS_M5_M4_DIR", "/default/m4"),
                             Path.home() / "private/m4")
            self.assertEqual(_configured_directory("VIDEOCHESS_M5_M3_RELEASE_DIR", "/default/m3"),
                             Path("/data/private/m3-r6"))
        self.assertEqual(EXPECTED, "724ac730f3c5f2d01b48b26eb7670a3c764978a3dd4d6702b3057a99ab1a90a4")

    def test_existing_initialization_snapshot_allows_only_metadata_only_recovery_revision(self):
        expected={'schema':'videochess-ddqn-evaluation-snapshot/2.0','resumable':False,
                  'config_sha256':'same-config','code_sha256':'current-source','stage':'pre_rl'}
        for allowed_code in RECOVERY_COMPATIBLE_CODE_SHA256:
            old=dict(expected); old['code_sha256']=allowed_code
            self.assertTrue(_compatible_initialization_metadata(old,expected))
            incompatible=dict(old); incompatible['config_sha256']='changed-config'
            self.assertFalse(_compatible_initialization_metadata(incompatible,expected))
        unknown=dict(expected); unknown['code_sha256']='0'*64
        self.assertFalse(_compatible_initialization_metadata(unknown,expected))

    @unittest.skipUnless((M4/'pretrained-behavior-only.pt').is_file(),'accepted local M4 artifact unavailable in this clone')
    def test_accepted_m4_shared_transfer_and_fresh_paired_q_head(self):
        path=M4/'pretrained-behavior-only.pt'
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),EXPECTED)
        self.assertEqual(len(verify_artifact_manifest(M4)['files']),19)
        source,bundle=load_checkpoint(path)
        self.assertEqual(bundle['metadata']['checkpoint_role'],'pretrained_behavior_only')
        warm=make_warm_scorer(source,q_head_seed=123)
        scratch=make_scratch_scorer(representation_seed=456,q_head_seed=123)
        for key,value in source.m5_transfer_state().items(): self.assertTrue(torch.equal(value,warm.state_dict()[key]))
        self.assertNotIn('behavior_head.weight',warm.state_dict())
        self.assertNotIn('behavior_head.bias',warm.state_dict())
        self.assertTrue(torch.equal(warm.q_head.weight,scratch.q_head.weight))
        self.assertTrue(torch.equal(warm.q_head.bias,scratch.q_head.bias))
        target=clone_target(warm)
        self.assertTrue(all(torch.equal(a,b) for a,b in zip(warm.parameters(),target.parameters())))
        warm_shared=warm.m5_transfer_state(); scratch_shared=scratch.m5_transfer_state()
        self.assertTrue(any(not torch.equal(warm_shared[k],scratch_shared[k]) for k in warm_shared))
