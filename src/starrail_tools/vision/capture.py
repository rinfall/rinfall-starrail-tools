import ctypes
from ctypes import wintypes
import numpy as np
import cv2
from starrail_tools.core.window import WindowManager
from starrail_tools.utils.logger import logger

class ScreenCapture:
    """Windows 静默后台截图器 (支持被遮挡时截图)"""

    def __init__(self, window_manager: WindowManager):
        self.wm = window_manager

    def capture(self) -> np.ndarray | None:
        """
        截取游戏客户区画面，返回 OpenCV BGR 格式的 numpy.ndarray
        """
        self.wm.update_client_rect()
        hwnd = self.wm.hwnd
        if not hwnd:
            logger.warning("截图失败: 未找到游戏窗口句柄")
            return None

        rect = self.wm.client_rect
        w, h = rect.width, rect.height
        if w <= 0 or h <= 0:
            logger.warning("截图失败: 客户区尺寸为 0")
            return None

        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32

        hwnd_dc = user32.GetDC(hwnd)
        mem_dc = gdi32.CreateCompatibleDC(hwnd_dc)
        bitmap = gdi32.CreateCompatibleBitmap(hwnd_dc, w, h)
        gdi32.SelectObject(mem_dc, bitmap)

        # PW_CLIENTONLY (1) | PW_RENDERFULLCONTENT (2) = 3
        # 支持在窗口被部分遮挡时完整截取内容
        success = user32.PrintWindow(hwnd, mem_dc, 3)
        if not success:
            # 降级尝试 BitBlt
            gdi32.BitBlt(mem_dc, 0, 0, w, h, hwnd_dc, 0, 0, 0x00CC0020)  # SRCCOPY

        # 提取位图数据到内存缓冲区
        bmp_info = np.zeros(1, dtype=[
            ('biSize', np.uint32),
            ('biWidth', np.int32),
            ('biHeight', np.int32),
            ('biPlanes', np.uint16),
            ('biBitCount', np.uint16),
            ('biCompression', np.uint32),
            ('biSizeImage', np.uint32),
            ('biXPelsPerMeter', np.int32),
            ('biYPelsPerMeter', np.int32),
            ('biClrUsed', np.uint32),
            ('biClrImportant', np.uint32),
        ])
        bmp_info['biSize'] = 40
        bmp_info['biWidth'] = w
        bmp_info['biHeight'] = -h  # 负高表示从上到下的扫描线，避免图像倒置
        bmp_info['biPlanes'] = 1
        bmp_info['biBitCount'] = 32
        bmp_info['biCompression'] = 0

        buffer = np.empty((h, w, 4), dtype=np.uint8)
        gdi32.GetDIBits(
            mem_dc, bitmap, 0, h,
            buffer.ctypes.data,
            bmp_info.ctypes.data,
            0  # DIB_RGB_COLORS
        )

        # 释放 GDI 句柄，防止内存泄露
        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(mem_dc)
        user32.ReleaseDC(hwnd, hwnd_dc)

        # BGRA -> BGR
        img_bgr = cv2.cvtColor(buffer, cv2.COLOR_BGRA2BGR)
        return img_bgr

    def capture_roi(self, rx1: float, ry1: float, rx2: float, ry2: float) -> np.ndarray | None:
        """
        截取指定比例区域 (rx1, ry1) 到 (rx2, ry2) 的小图
        """
        full_img = self.capture()
        if full_img is None:
            return None

        h, w = full_img.shape[:2]
        x1 = max(0, int(w * rx1))
        y1 = max(0, int(h * ry1))
        x2 = min(w, int(w * rx2))
        y2 = min(h, int(h * ry2))

        if x2 <= x1 or y2 <= y1:
            return None

        return full_img[y1:y2, x1:x2].copy()
