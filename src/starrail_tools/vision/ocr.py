import re
import numpy as np
from typing import NamedTuple
from starrail_tools.utils.logger import logger

class TextMatch(NamedTuple):
    text: str
    center_rx: float
    center_ry: float
    confidence: float

class OcrEngine:
    """OCR 识别引擎封装 (采用轻量 ONNX 推理)"""

    _instance = None

    def __init__(self):
        self._engine = None

    def _get_engine(self):
        if self._engine is None:
            try:
                from rapidocr import RapidOCR
                self._engine = RapidOCR(params={"Global.log_level": "error"})
                logger.debug("RapidOCR 引擎初始化完成")
            except ImportError:
                logger.error("请先安装 rapidocr-onnxruntime: pip install rapidocr-onnxruntime")
                raise
        return self._engine

    def recognize_cropped_text(self, cropped_binary_img: np.ndarray) -> str:
        """
        对已二值化的小图仅进行纯文本识别 (跳过耗时的全屏文字检测网络)
        """
        engine = self._get_engine()
        # use_det=False: 直接将裁剪图送入识别网络 SVTR，极速 (10~20ms)
        output = engine(cropped_binary_img, use_det=False, use_cls=False, use_rec=True)
        if not output or not output.txts:
            return ""
        return "".join(output.txts).strip()

    def find_text(self, img: np.ndarray, target: str, confidence_thresh: float = 0.7) -> TextMatch | None:
        """
        在图像中检索指定目标文字，返回中心相对坐标
        """
        engine = self._get_engine()
        output = engine(img, use_det=True, use_cls=False, use_rec=True)
        if not output or not output.txts:
            return None

        h, w = img.shape[:2]
        for box, text, score in zip(output.boxes, output.txts, output.scores):
            if score >= confidence_thresh and target in text:
                # box: 4 个顶点坐标 [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                box_np = np.array(box)
                center_x = float(np.mean(box_np[:, 0]))
                center_y = float(np.mean(box_np[:, 1]))
                return TextMatch(
                    text=text,
                    center_rx=center_x / w,
                    center_ry=center_y / h,
                    confidence=float(score)
                )
        return None

    @staticmethod
    def extract_stamina_ratio(text: str) -> tuple[int, int] | None:
        """
        从 OCR 文本中提取当前开拓力与上限 (例如 '180/240' -> (180, 240))
        """
        # 清理常见 OCR 杂质符号
        cleaned = text.replace('十', '+').replace('满', '').strip()
        match = re.search(r'(\d+)\s*/\s*(\d+)', cleaned)
        if match:
            return int(match.group(1)), int(match.group(2))
        return None
