import cv2
import numpy as np
from pathlib import Path
from typing import NamedTuple
from starrail_tools.utils.logger import logger

class MatchResult(NamedTuple):
    found: bool
    center_rx: float
    center_ry: float
    confidence: float

class TemplateMatcher:
    """OpenCV 模板匹配与带掩码（Mask）的高确定性匹配器"""

    def __init__(self, templates_dir: str | Path = "resources/templates"):
        self.templates_dir = Path(templates_dir)
        self._cache: dict[str, tuple[np.ndarray, np.ndarray | None]] = {}

    def load_template(self, name: str) -> tuple[np.ndarray, np.ndarray | None]:
        """
        加载模板图及 Alpha 掩码通道 (如果存在)
        """
        if name in self._cache:
            return self._cache[name]

        path = self.templates_dir / f"{name}.png"
        if not path.exists():
            raise FileNotFoundError(f"未找到模板图片文件: {path}")

        # 读取 4 通道（包含 Alpha 透明通道）
        raw = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if raw is None:
            raise ValueError(f"无法解析模板图片: {path}")

        if raw.shape[2] == 4:
            template = cv2.cvtColor(raw[:, :, :3], cv2.COLOR_BGR2GRAY)
            mask = raw[:, :, 3]  # Alpha 通道作为掩码
        else:
            template = cv2.cvtColor(raw, cv2.COLOR_BGR2GRAY)
            mask = None

        self._cache[name] = (template, mask)
        return template, mask

    def match(self, screen_img: np.ndarray, template_name: str, threshold: float = 0.82) -> MatchResult:
        """
        在屏幕图像中搜索指定模板
        :return: MatchResult(found, center_rx, center_ry, confidence)
        """
        try:
            template, mask = self.load_template(template_name)
        except Exception as e:
            logger.debug(f"加载模板 {template_name} 失败: {e}")
            return MatchResult(False, 0.0, 0.0, 0.0)

        # 转灰度
        if len(screen_img.shape) == 3:
            gray_screen = cv2.cvtColor(screen_img, cv2.COLOR_BGR2GRAY)
        else:
            gray_screen = screen_img

        sh, sw = gray_screen.shape[:2]
        th, tw = template.shape[:2]
        if sh < th or sw < tw:
            return MatchResult(False, 0.0, 0.0, 0.0)

        if mask is not None:
            # 带掩码的归一化互相关匹配
            res = cv2.matchTemplate(gray_screen, template, cv2.TM_CCORR_NORMED, mask=mask)
        else:
            res = cv2.matchTemplate(gray_screen, template, cv2.TM_CCOEFF_NORMED)

        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        confidence = float(max_val)

        if confidence >= threshold:
            center_x = max_loc[0] + tw / 2.0
            center_y = max_loc[1] + th / 2.0
            return MatchResult(
                found=True,
                center_rx=center_x / sw,
                center_ry=center_y / sh,
                confidence=confidence
            )

        return MatchResult(False, 0.0, 0.0, confidence)
