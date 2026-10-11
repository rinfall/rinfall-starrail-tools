import ctypes
from ctypes import wintypes
import time
from typing import NamedTuple
from starrail_tools.utils.logger import logger

# 启用 Per-Monitor DPI 识别，确保窗口尺寸与坐标获取绝对精确
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

class Rect(NamedTuple):
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

class WindowManager:
    """星穹铁道游戏窗口管理与坐标换算器"""

    GAME_TITLES = ["崩坏：星穹铁道", "Honkai: Star Rail"]

    def __init__(self):
        self.hwnd: int = 0
        self.client_rect: Rect = Rect(0, 0, 0, 0)

    def find_window(self) -> int:
        """查找游戏窗口句柄"""
        user32 = ctypes.windll.user32
        for title in self.GAME_TITLES:
            hwnd = user32.FindWindowW(None, title)
            if hwnd:
                self.hwnd = hwnd
                self.update_client_rect()
                return hwnd
        self.hwnd = 0
        return 0

    def is_running(self) -> bool:
        """检查游戏窗口是否已存在"""
        return self.find_window() != 0

    def update_client_rect(self) -> Rect:
        """更新窗口客户区实际屏幕坐标"""
        if not self.hwnd:
            return Rect(0, 0, 0, 0)
        
        user32 = ctypes.windll.user32
        rect = wintypes.RECT()
        user32.GetClientRect(self.hwnd, ctypes.byref(rect))

        # 将客户区左上角 (0, 0) 映射到屏幕物理坐标
        point = wintypes.POINT(0, 0)
        user32.ClientToScreen(self.hwnd, ctypes.byref(point))

        self.client_rect = Rect(
            left=point.x,
            top=point.y,
            right=point.x + rect.right,
            bottom=point.y + rect.bottom
        )
        return self.client_rect

    def activate(self) -> bool:
        """激活并置顶游戏窗口"""
        if not self.hwnd and not self.find_window():
            logger.warning("未找到游戏窗口，无法激活")
            return False

        user32 = ctypes.windll.user32
        # 解除最小化
        if user32.IsIconic(self.hwnd):
            user32.ShowWindow(self.hwnd, 9)  # SW_RESTORE
            time.sleep(0.3)

        # 模拟一次系统按键解除 SetForegroundWindow 限制
        user32.keybd_event(0x12, 0, 0, 0)  # ALT 按下
        user32.keybd_event(0x12, 0, 2, 0)  # ALT 抬起
        user32.SetForegroundWindow(self.hwnd)
        self.update_client_rect()
        logger.debug(f"已激活游戏窗口，客户区尺寸: {self.client_rect.width}x{self.client_rect.height}")
        return True

    def to_screen_coord(self, rx: float, ry: float) -> tuple[int, int]:
        """
        将基于标准 16:9 比例的浮点相对坐标 (0.0~1.0)
        换算为当前客户区实际的屏幕绝对物理坐标 (X, Y)
        """
        self.update_client_rect()
        if self.client_rect.width == 0 or self.client_rect.height == 0:
            raise RuntimeError("游戏客户区尺寸异常，请确保窗口已正确显示")

        abs_x = int(self.client_rect.left + self.client_rect.width * rx)
        abs_y = int(self.client_rect.top + self.client_rect.height * ry)
        return abs_x, abs_y
