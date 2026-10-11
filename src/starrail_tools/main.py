import os
import sys
from pathlib import Path
from starrail_tools.config.models import AppConfig
from starrail_tools.utils.logger import setup_logger, logger
from starrail_tools.core.window import WindowManager
from starrail_tools.core.input import InputController
from starrail_tools.core.state_machine import StateMachine
from starrail_tools.vision.capture import ScreenCapture
from starrail_tools.vision.matcher import TemplateMatcher
from starrail_tools.vision.ocr import OcrEngine
from starrail_tools.tasks.login import LoginTask
from starrail_tools.tasks.stamina import StaminaTask

def handle_post_action(action: str):
    """任务完成后的系统行为处置"""
    logger.info(f"执行收尾行为: {action}")
    if action == "close_game":
        logger.info("正在关闭游戏进程...")
        os.system("taskkill /f /im StarRail.exe >nul 2>&1")
    elif action == "sleep":
        logger.info("系统即将在 10 秒后进入休眠...")
        os.system("timeout /t 10 & rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
    elif action == "shutdown":
        logger.info("系统即将在 30 秒后关机...")
        os.system("shutdown /s /t 30")
    else:
        logger.info("任务执行完毕，游戏保持运行。")

def main():
    logger.info("========================================")
    logger.info("  Rinfall StarRail Tools (RST) v0.1.0   ")
    logger.info("========================================")

    # 1. 加载配置
    config = AppConfig.load("config.yaml")
    setup_logger(config.system.log_level)
    logger.info(f"配置文件加载完成，目标副本: {config.stamina.target_dungeon}")

    # 2. 组装核心驱动引擎
    wm = WindowManager()
    capture = ScreenCapture(wm)
    input_ctrl = InputController(wm)
    matcher = TemplateMatcher("resources/templates")
    ocr = OcrEngine()
    fsm = StateMachine(wm, capture, input_ctrl, matcher, ocr)

    # 3. 执行任务编排
    try:
        # 步骤 1~3: 启动/激活与登录检查
        login_task = LoginTask(config, wm, capture, input_ctrl, matcher, ocr, fsm)
        if not login_task.run():
            logger.error("登录与大世界接入失败，终止后续任务")
            sys.exit(1)

        # 步骤 4~7: 检查体力与副本战斗循环
        stamina_task = StaminaTask(config, wm, capture, input_ctrl, matcher, ocr, fsm)
        stamina_task.run()

        logger.info("🎉 今日星铁日常核心任务全流程执行完毕！")

        # 4. 执行收尾处置
        handle_post_action(config.system.post_action)

    except KeyboardInterrupt:
        logger.warning("用户手动中止执行")
    except Exception as e:
        logger.exception(f"执行过程中发生未捕获异常: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
