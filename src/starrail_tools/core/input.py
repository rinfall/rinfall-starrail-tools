import random
import time
import pyautogui
import pyperclip
from starrail_tools.core.window import WindowManager
from starrail_tools.utils.logger import logger

# 安全开关：防止极端情况下鼠标飞出导致死锁
pyautogui.FAILSAFE = False

class InputController:
    """键鼠输入仿真与时序控制器"""

    def __init__(self, window_manager: WindowManager):
        self.wm = window_manager

    def click(self, rx: float, ry: float, jitter: int = 2, after_sleep: float = 0.3):
        """
        根据比例坐标点击指定位置
        :param rx: 相对 X 比例 (0.0~1.0)
        :param ry: 相对 Y 比例 (0.0~1.0)
        :param jitter: 拟人化随机微小像素偏移
        :param after_sleep: 点击后休眠时间(秒)
        """
        self.wm.activate()
        abs_x, abs_y = self.wm.to_screen_coord(rx, ry)

        if jitter > 0:
            abs_x += random.randint(-jitter, jitter)
            abs_y += random.randint(-jitter, jitter)

        pyautogui.click(abs_x, abs_y)
        logger.debug(f"点击位置: ({rx:.3f}, {ry:.3f}) -> 绝对物理坐标 ({abs_x}, {abs_y})")
        if after_sleep > 0:
            time.sleep(after_sleep)

    def press_key(self, key: str, presses: int = 1, interval: float = 0.1, after_sleep: float = 0.2):
        """
        模拟按下键盘按键 (如 'f', 'v', 'esc', 'space')
        """
        self.wm.activate()
        pyautogui.press(key, presses=presses, interval=interval)
        logger.debug(f"按下按键: '{key}' (次数: {presses})")
        if after_sleep > 0:
            time.sleep(after_sleep)

    def paste(self, text: str, after_sleep: float = 0.3):
        """
        通过剪贴板安全粘贴文本，规避字符逐个模拟漏按和输入法异常
        """
        self.wm.activate()
        pyperclip.copy(text)
        time.sleep(0.05)
        pyautogui.hotkey('ctrl', 'v')
        logger.debug(f"已粘贴文本: {text[:2]}***{text[-2:] if len(text)>4 else ''}")
        if after_sleep > 0:
            time.sleep(after_sleep)
