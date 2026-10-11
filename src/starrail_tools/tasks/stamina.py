import time
from starrail_tools.tasks.base import BaseTask
from starrail_tools.core.state_machine import PageState
from starrail_tools.vision.preprocessor import ImagePreprocessor
from starrail_tools.utils.logger import logger

class StaminaTask(BaseTask):
    """自动体力刷取与副本战斗闭环任务"""

    def run(self) -> bool:
        logger.info("=== 阶段：检查开拓力并执行副本刷取 ===")

        # 1. 确保在大世界可操作状态
        if not self.fsm.ensure_state(PageState.MAIN_WORLD, max_retries=5):
            logger.error("无法对齐至大世界状态，任务中止")
            return False

        # 2. 唤起生存索引并读取体力
        current_stamina, max_stamina = self._read_stamina()
        if current_stamina < 0:
            logger.error("读取体力失败，无法继续")
            return False

        logger.info(f"📊 当前开拓力: {current_stamina} / {max_stamina} (保留阈值: {self.config.stamina.reserve_stamina})")
        if current_stamina <= self.config.stamina.reserve_stamina or current_stamina < 10:
            logger.info("✅ 当前体力不足单次消耗或已达到保留阈值，无需刷取。")
            self.input.press_key("esc", after_sleep=1.0)
            return True

        # 3. 导航并进入目标副本
        if not self._navigate_to_dungeon():
            logger.error("导航并传送至副本失败")
            return False

        # 4. 执行战斗与结算循环
        return self._combat_loop(current_stamina)

    def _read_stamina(self) -> tuple[int, int]:
        """按 F4 打开指南，通过局部二值化 OCR 读取体力"""
        logger.info("正在唤起生存索引读取体力...")
        self.input.press_key("f4", after_sleep=1.5)

        img = self.capture.capture()
        if img is None:
            return -1, -1

        # 裁剪右上角体力区域 (以标准比例约 0.68~0.90 X, 0.038~0.082 Y)
        roi = ImagePreprocessor.crop_ratio(img, 0.68, 0.038, 0.90, 0.082)
        binary_roi = ImagePreprocessor.clean_number_roi(roi)

        text = self.ocr.recognize_cropped_text(binary_roi)
        logger.debug(f"体力局部 OCR 原始识别文本: '{text}'")

        res = self.ocr.extract_stamina_ratio(text)
        if res:
            return res

        # 兜底：如果直接二值化未扫出斜杠，尝试直接在原 ROI 上做通用识别
        full_text = self.ocr.recognize_cropped_text(roi)
        res = self.ocr.extract_stamina_ratio(full_text)
        if res:
            return res

        return -1, -1

    def _navigate_to_dungeon(self) -> bool:
        """在生存索引列表中匹配目标副本并传送"""
        target = self.config.stamina.target_dungeon
        logger.info(f"正在定位目标副本: '{target}'...")

        img = self.capture.capture()
        match = self.ocr.find_text(img, target)
        if not match:
            # 尝试切换左侧标签或微调
            logger.warning(f"当前页面未直接看到 '{target}'，尝试在默认关卡传送...")

        # 点击右侧对应的“传送”按钮（通用比例位置：右下角偏内侧或直接点击当前选中行的传送）
        logger.info("点击传送并等待场景加载...")
        self.input.click(0.85, 0.88, after_sleep=3.0)

        # 等待黑屏传送完成，直到重新回到大世界
        time.sleep(2.0)
        if not self.fsm.ensure_state(PageState.MAIN_WORLD, max_retries=10, interval=1.5):
            logger.error("传送后等待场景加载超时")
            return False

        # 传送落地，此时角色正对副本入口锚点，按 F 交互进本
        logger.info("到达副本锚点，按下 F 键交互进入副本...")
        self.input.press_key("f", after_sleep=2.0)

        # 确认进入编队/挑战准备页面
        if not self.fsm.ensure_state(PageState.TEAM_PREPARE, max_retries=6):
            logger.warning("未检测到编队确认页，尝试盲点右下角开始挑战...")

        # 点击右下角“开始挑战” (0.88, 0.92)
        logger.info("点击「开始挑战」进入战斗...")
        self.input.click(0.88, 0.92, after_sleep=2.5)
        return True

    def _combat_loop(self, start_stamina: int) -> bool:
        """全自动战斗循环、托管与结算控制"""
        max_runs = self.config.stamina.max_runs
        runs_completed = 0
        logger.info(f"开始自动战斗监控 (计划最多完成 {max_runs} 轮)...")

        while runs_completed < max_runs:
            logger.info(f"--- 正在执行第 {runs_completed + 1} 轮战斗 ---")

            # 等待进入战斗场景
            combat_loaded = False
            for _ in range(15):
                state = self.fsm.detect_state()
                if state == PageState.IN_BATTLE:
                    combat_loaded = True
                    break
                time.sleep(1.0)

            if combat_loaded:
                logger.info("战斗场景已加载，激活游戏内置自动战斗 (V 键)...")
                self.input.press_key("v", after_sleep=0.5)

            # 低频轮询等待战斗结算
            logger.info("正在挂机等待战斗胜利结算...")
            settled = False
            deadline = time.time() + 300  # 单场最长 5 分钟
            while time.time() < deadline:
                state = self.fsm.detect_state()
                if state == PageState.BATTLE_SETTLE:
                    settled = True
                    break
                time.sleep(2.5)

            if not settled:
                logger.error("等待战斗结算超时！")
                return False

            runs_completed += 1
            logger.info(f"第 {runs_completed} 轮战斗结算完成！")

            # 判定是否还能继续连刷
            if runs_completed >= max_runs:
                logger.info("已达到设定最大连刷次数，退出战斗。")
                self.input.click(0.28, 0.92, after_sleep=2.0)  # 点击退出战斗
                break

            # 点击“再次挑战” (比例坐标约 0.72, 0.92)
            logger.info("体力尚存，点击「再次挑战」继续...")
            self.input.click(0.72, 0.92, after_sleep=2.5)

        logger.info(f"🎉 副本刷取完成！共执行 {runs_completed} 轮。")
        self.fsm.ensure_state(PageState.MAIN_WORLD, max_retries=6)
        return True
