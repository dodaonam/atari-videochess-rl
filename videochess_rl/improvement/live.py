"""Optional local Tk RGB viewer; frames remain local and are never uploaded."""
import time
from videochess_rl.environment import VideoChessEnv


class LiveEnvironment(VideoChessEnv):
    def __init__(self,config):
        super().__init__(config)
        import tkinter as tk
        self.window=tk.Tk();self.window.title('VideoChess — live RGB observation')
        self.label=tk.Label(self.window);self.label.pack()
        self.last=0

    def _frame(self,*args,**kwargs):
        frame=super()._frame(*args,**kwargs)
        if time.monotonic()-self.last>.04:
            import tkinter as tk
            rgb=frame.rgb
            ppm=f'P6\n{rgb.shape[1]} {rgb.shape[0]}\n255\n'.encode()+rgb.tobytes()
            self.image=tk.PhotoImage(data=ppm,format='PPM').zoom(3,3)
            self.label.configure(image=self.image)
            self.window.title(f'VideoChess — observed ALE frame {frame.frame_number}')
            self.window.update()
            self.last=time.monotonic()
        return frame

    def close(self):
        try:self.window.destroy()
        finally:super().close()
