import sys
from pathlib import Path

# 将 src 添加到导入路径
src_path = Path(__file__).resolve().parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from starrail_tools.config.models import AppConfig
from starrail_tools.utils.logger import setup_logger, logger
from starrail_tools.utils.recorder import WindowRecorder
from starrail_tools.core.window import WindowManager
from starrail_tools.core.input import InputController
from starrail_tools.core.state_machine import StateMachine
from starrail_tools.vision.capture import ScreenCapture
from starrail_tools.vision.matcher import TemplateMatcher
from starrail_tools.vision.ocr import OcrEngine
from starrail_tools.tasks.login import LoginTask

def run_test():
    logger.info("========================================")
    logger.info("  【专项测试】启动游戏 -> 登录进入游戏  ")
    logger.info("========================================")

    # 1. 加载配置
    config = AppConfig.load("config.yaml")
    setup_logger(config.system.log_level)
    logger.info(f"游戏路径: {config.game.path}")

    # 2. 组装核心驱动引擎
    wm = WindowManager()
    capture = ScreenCapture(wm)
    input_ctrl = InputController(wm)
    matcher = TemplateMatcher("resources/templates")
    ocr = OcrEngine()
    fsm = StateMachine(wm, capture, input_ctrl, matcher, ocr)

    # 3. 启动自动录屏 (每秒 10 帧，压缩为 720p，清晰且文件小)
    video_path = Path("logs/test_login_recording.mp4").resolve()
    recorder = WindowRecorder(capture, output_path=video_path, fps=10)
    recorder.start()

    success = False
    try:
        # 4. 执行登录与大世界接入流程
        login_task = LoginTask(config, wm, capture, input_ctrl, matcher, ocr, fsm)
        success = login_task.run()
        if success:
            logger.info("🎉 专项测试成功：已顺利穿透登录流程并成功抵达大世界！")
        else:
            logger.error("❌ 专项测试失败：未能顺利进入大世界，请查看录屏与日志。")
    except KeyboardInterrupt:
        logger.warning("用户手动中止测试")
    except Exception as e:
        logger.exception(f"测试过程发生未捕获异常: {e}")
    finally:
        # 5. 停止录屏并输出视频路径
        recorder.stop()
        if video_path.exists():
            size_mb = video_path.stat().st_size / (1024 * 1024)
            logger.info(f"📹 录屏文件已生成: {video_path} ({size_mb:.2f} MB)")
            print(f"\n[录屏保存位置] file:///{video_path.as_posix()}\n")

    return success

if __name__ == "__main__":
    run_test()
