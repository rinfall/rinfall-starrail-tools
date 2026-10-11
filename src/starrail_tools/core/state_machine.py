from enum import Enum, auto
import time
from starrail_tools.core.window import WindowManager
from starrail_tools.core.input import InputController
from starrail_tools.vision.capture import ScreenCapture
from starrail_tools.vision.matcher import TemplateMatcher
from starrail_tools.vision.ocr import OcrEngine
from starrail_tools.utils.logger import logger

class PageState(Enum):
    UNKNOWN = auto()
    LOGIN_TITLE = auto()          # 登录标题界面（有“开始游戏”/“点击进入”）
    LOGIN_CREDENTIALS = auto()    # 账号密码输入弹窗
    LOGIN_CAPTCHA = auto()        # 滑块拼图阻断
    MAIN_WORLD = auto()           # 可自由行动的大世界
    GUIDE_PAGE = auto()           # 星际和平指南 / 生存索引
    TEAM_PREPARE = auto()         # 副本编队准备界面（有“开始挑战”）
    IN_BATTLE = auto()            # 战斗进行中
    BATTLE_SETTLE = auto()        # 战斗结算页（有“再次挑战”或“退出战斗”）
    POPUP_DIALOG = auto()         # 阻断性弹窗（签到、公告、月卡、更新提示）

class StateMachine:
    """页面指纹状态机与自愈调度器"""

    def __init__(
        self,
        window_manager: WindowManager,
        capture: ScreenCapture,
        input_controller: InputController,
        matcher: TemplateMatcher,
        ocr: OcrEngine
    ):
        self.wm = window_manager
        self.capture = capture
        self.input = input_controller
        self.matcher = matcher
        self.ocr = ocr

    def detect_state(self) -> PageState:
        """根据当前游戏截图分析页面状态指纹"""
        img = self.capture.capture()
        if img is None:
            return PageState.UNKNOWN

        # 1. 检查是否在战斗中 (右上角自动战斗图标 / 技能按键)
        battle_match = self.matcher.match(img, "btn_auto_battle", threshold=0.80)
        if battle_match.found:
            return PageState.IN_BATTLE

        # 2. 检查是否在结算页面 (再次挑战 / 退出战斗图标)
        again_match = self.matcher.match(img, "btn_again", threshold=0.80)
        quit_battle_match = self.matcher.match(img, "btn_quit_battle", threshold=0.80)
        if again_match.found or quit_battle_match.found:
            return PageState.BATTLE_SETTLE

        # 3. 检查是否在编队界面 (右下角“开始挑战”)
        team_match = self.matcher.match(img, "btn_start_challenge", threshold=0.80)
        if team_match.found:
            return PageState.TEAM_PREPARE

        # 4. 检查是否在大世界 (左上角小地图 / 手机菜单图标)
        minimap_match = self.matcher.match(img, "icon_minimap", threshold=0.75)
        if minimap_match.found:
            return PageState.MAIN_WORLD

        # 5. 检查登录相关页面 (通过 OCR)
        # 优先检测滑块验证码
        if self.ocr.find_text(img, "请拖动滑块完成拼图", confidence_thresh=0.7):
            return PageState.LOGIN_CAPTCHA

        if self.ocr.find_text(img, "点击进入", confidence_thresh=0.7) or \
           self.ocr.find_text(img, "开始游戏", confidence_thresh=0.7):
            return PageState.LOGIN_TITLE

        if self.ocr.find_text(img, "请输入密码", confidence_thresh=0.7) or \
           self.ocr.find_text(img, "其他账号", confidence_thresh=0.7):
            return PageState.LOGIN_CREDENTIALS

        # 6. 检查是否在生存索引界面
        if self.ocr.find_text(img, "生存索引", confidence_thresh=0.7) or \
           self.ocr.find_text(img, "星际和平指南", confidence_thresh=0.7):
            return PageState.GUIDE_PAGE

        # 7. 检查通用弹窗（包含“确认”、“取消”、“同意并继续”等）
        if self.ocr.find_text(img, "同意并继续", confidence_thresh=0.7) or \
           self.ocr.find_text(img, "确认", confidence_thresh=0.7):
            return PageState.POPUP_DIALOG

        return PageState.UNKNOWN

    def ensure_state(self, target_state: PageState, max_retries: int = 6, interval: float = 1.0) -> bool:
        """
        断言并尝试将画面自愈恢复至指定状态
        若检测到意外弹窗，自动发送 ESC 进行回退自愈
        """
        for i in range(max_retries):
            current = self.detect_state()
            logger.debug(f"[{i+1}/{max_retries}] 当前状态: {current.name}, 目标状态: {target_state.name}")
            if current == target_state:
                return True

            if current == PageState.POPUP_DIALOG:
                logger.info("检测到阻断弹窗，按 ESC 自动关闭...")
                self.input.press_key("esc", after_sleep=1.0)
            elif current == PageState.UNKNOWN:
                # 盲点屏幕空白处尝试消去通知浮层
                self.input.click(0.5, 0.2, after_sleep=0.5)

            time.sleep(interval)

        return False
