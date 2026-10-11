import cv2
import numpy as np

class ImagePreprocessor:
    """图像二值化与字符增强预处理器 (消除星空动态背景干扰)"""

    @staticmethod
    def crop_ratio(img: np.ndarray, rx1: float, ry1: float, rx2: float, ry2: float) -> np.ndarray:
        """按相对比例裁剪图像"""
        h, w = img.shape[:2]
        x1 = max(0, int(w * rx1))
        y1 = max(0, int(h * ry1))
        x2 = min(w, int(w * rx2))
        y2 = min(h, int(h * ry2))
        return img[y1:y2, x1:x2].copy()

    @staticmethod
    def to_white_text_binarize(img: np.ndarray, thresh: int = 190) -> np.ndarray:
        """
        适用于星铁通用白字（如体力数值、大部分按钮文本）
        将白色字符提取为纯白(255)，半透明黑色和彩色光效背景抹为纯黑(0)
        """
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()

        # 简单高效的高阈值二值化
        _, binary = cv2.threshold(gray, thresh, 255, cv2.THRESH_BINARY)
        return binary

    @staticmethod
    def to_gold_text_binarize(img: np.ndarray) -> np.ndarray:
        """
        适用于星铁重点金色文字/数字（如体力高亮、星琼数值）
        在 HSV 色彩空间精确截取金色范围
        """
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        # 星铁金色 HSV 范围（色相约 15~35，饱和度 > 80，亮度 > 150）
        lower_gold = np.array([15, 80, 150])
        upper_gold = np.array([35, 255, 255])
        mask = cv2.inRange(hsv, lower_gold, upper_gold)
        return mask

    @staticmethod
    def clean_number_roi(img: np.ndarray) -> np.ndarray:
        """
        专用数字预处理：放大并二值化，使 OCR 引擎极度易读
        """
        # 放大 1.5 倍以增强小字号数字边缘清晰度
        h, w = img.shape[:2]
        resized = cv2.resize(img, (int(w * 1.5), int(h * 1.5)), interpolation=cv2.INTER_CUBIC)
        binary = ImagePreprocessor.to_white_text_binarize(resized, thresh=185)
        return binary
