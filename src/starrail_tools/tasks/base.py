from abc import ABC, abstractmethod
from starrail_tools.config.models import AppConfig
from starrail_tools.core.window import WindowManager
from starrail_tools.core.input import InputController
from starrail_tools.core.state_machine import StateMachine
from starrail_tools.vision.capture import ScreenCapture
from starrail_tools.vision.matcher import TemplateMatcher
from starrail_tools.vision.ocr import OcrEngine

class BaseTask(ABC):
    """自动化任务执行基类"""

    def __init__(
        self,
        config: AppConfig,
        window_manager: WindowManager,
        capture: ScreenCapture,
        input_controller: InputController,
        matcher: TemplateMatcher,
        ocr: OcrEngine,
        state_machine: StateMachine
    ):
        self.config = config
        self.wm = window_manager
        self.capture = capture
        self.input = input_controller
        self.matcher = matcher
        self.ocr = ocr
        self.fsm = state_machine

    @abstractmethod
    def run(self) -> bool:
        """执行任务逻辑，返回是否成功完成"""
        pass
