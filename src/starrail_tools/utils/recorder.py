import threading
import time
from pathlib import Path
import cv2
import numpy as np
from starrail_tools.vision.capture import ScreenCapture
from starrail_tools.utils.logger import logger

class WindowRecorder:
    """游戏窗口自动录屏器 (采用轻量后台线程抽帧并编码为 MP4 视频)"""

    def __init__(
        self,
        capture: ScreenCapture,
        output_path: str | Path = "logs/test_login_recording.mp4",
        fps: int = 10,
        resolution: tuple[int, int] = (1280, 720)
    ):
        self.capture = capture
        self.output_path = Path(output_path)
        self.fps = fps
        self.resolution = resolution
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self):
        """开启后台录屏线程"""
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._record_loop, daemon=True)
        self._thread.start()
        logger.info(f"🎥 自动录屏已启动，视频将实时保存至: {self.output_path}")

    def stop(self):
        """停止录屏并保存文件"""
        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join(timeout=6.0)
            logger.info(f"🎥 自动录屏已结束并保存: {self.output_path}")

    def _record_loop(self):
        writer = None
        interval = 1.0 / self.fps
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')

        while not self._stop_event.is_set():
            t0 = time.time()
            img = self.capture.capture()
            if img is not None:
                if writer is None:
                    writer = cv2.VideoWriter(
                        str(self.output_path),
                        fourcc,
                        float(self.fps),
                        self.resolution
                    )
                frame = cv2.resize(img, self.resolution, interpolation=cv2.INTER_AREA)
                writer.write(frame)

            elapsed = time.time() - t0
            sleep_time = max(0.01, interval - elapsed)
            time.sleep(sleep_time)

        if writer is not None:
            writer.release()
