import subprocess
import time
from pathlib import Path
from starrail_tools.tasks.base import BaseTask
from starrail_tools.core.state_machine import PageState
from starrail_tools.utils.logger import logger

class LoginTask(BaseTask):
    """游戏启动与登录引导任务"""

    def run(self) -> bool:
        logger.info("=== 阶段：检查游戏运行状态与登录 ===")

        # 1. 检查游戏是否已运行
        if not self.wm.is_running():
            logger.info("未检测到游戏运行，正在拉起游戏主程序...")
            if not self._launch_game():
                return False
        else:
            logger.info("检测到游戏已在运行，正在激活并置顶窗口...")
            self.wm.activate()

        # 2. 等待并处理登录流程
        return self._handle_login_flow()

    def _launch_game(self) -> bool:
        game_path = Path(self.config.game.path)
        if not game_path.exists() or not game_path.is_file():
            logger.error(f"游戏路径不存在或无效: {game_path}，请检查 config.yaml")
            return False

        try:
            subprocess.Popen([str(game_path)], cwd=str(game_path.parent))
            logger.info(f"已拉起游戏进程，等待窗口创建 (最长 {self.config.game.launch_timeout} 秒)...")
        except Exception as e:
            logger.error(f"拉起游戏失败: {e}")
            return False

        deadline = time.time() + self.config.game.launch_timeout
        while time.time() < deadline:
            if self.wm.find_window():
                logger.info("成功捕获游戏窗口句柄！")
                time.sleep(3.0)  # 等待渲染引擎初始化
                self.wm.activate()
                return True
            time.sleep(1.5)

        logger.error("等待游戏窗口超时，启动中止")
        return False

    def _handle_login_flow(self) -> bool:
        deadline = time.time() + 180  # 最长 3 分钟完成进入大世界
        logger.info("开始监测并推进登录流程...")

        while time.time() < deadline:
            state = self.fsm.detect_state()
            logger.debug(f"当前登录阶段指纹: {state.name}")

            if state == PageState.MAIN_WORLD:
                logger.info("✅ 成功进入大世界！角色已就绪。")
                return True

            elif state == PageState.LOGIN_TITLE:
                logger.info("处于标题界面，点击进入游戏...")
                self.input.click(0.5, 0.67, after_sleep=2.5)

            elif state == PageState.LOGIN_CREDENTIALS:
                if self.config.account.auto_login:
                    logger.info("处于账密输入页，执行自动填充...")
                    self._fill_credentials()
                else:
                    logger.warning("需要输入账号密码，但未开启 auto_login，等待用户手动登录...")
                    time.sleep(3.0)

            elif state == PageState.LOGIN_CAPTCHA:
                logger.warning("⚠️ 检测到滑块拼图验证码！请在游戏窗口中手动滑动完成验证 (限时 120 秒)...")
                time.sleep(3.0)

            elif state == PageState.POPUP_DIALOG:
                logger.info("检测到登录弹窗/协议，尝试确认关闭...")
                # 优先点击“同意并继续”或按 ESC
                agree_box = self.ocr.find_text(self.capture.capture(), "同意")
                if agree_box:
                    self.input.click(agree_box.center_rx, agree_box.center_ry, after_sleep=1.0)
                else:
                    self.input.press_key("esc", after_sleep=1.0)

            else:
                # 过渡阶段（黑屏加载或过场动画），盲点屏幕中心推进
                self.input.click(0.5, 0.5, after_sleep=1.5)

        logger.error("登录超时，未能顺利进入大世界")
        return False

    def _fill_credentials(self):
        user = self.config.account.username
        pwd = self.config.account.password
        if not user or not pwd:
            logger.error("自动登录配置中的账号或密码为空！")
            return

        # 点击账号框（基于通用比例坐标），粘贴账号
        self.input.click(0.5, 0.38, after_sleep=0.5)
        self.input.paste(user)

        # Tab 键切换到密码框，粘贴密码
        self.input.press_key("tab", after_sleep=0.3)
        self.input.paste(pwd)

        # 点击协议勾选框与登录按钮
        self.input.click(0.42, 0.55, after_sleep=0.3)  # 勾选协议
        self.input.click(0.50, 0.62, after_sleep=2.0)  # 点击登录
