"""
OCR 识别服务
封装 PaddleOCR，支持图片文字提取 + 版面分析
PaddleOCR 为可选依赖，未安装时返回占位结果
"""
from pathlib import Path
from typing import Optional

from backend.utils.logger import logger

# 尝试导入 PaddleOCR（可选依赖）
try:
    from paddleocr import PaddleOCR as PaddleOCRClient
    HAS_PADDLE = True
except ImportError:
    HAS_PADDLE = False
    logger.warning("PaddleOCR not installed. OCR features will be unavailable.")
    logger.warning("Install: pip install paddlepaddle paddleocr")

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class OCRResult:
    """OCR 识别结果"""
    def __init__(self, text: str, paragraphs: Optional[list[dict]] = None):
        self.text = text                  # 全部识别文本
        self.paragraphs = paragraphs or []  # [{text, confidence, bbox}]


class OCRService:
    """OCR 识别服务"""

    def __init__(self):
        self._ocr: Optional[PaddleOCRClient] = None
        self._initialized = False

    def _ensure_initialized(self):
        """延迟初始化 PaddleOCR"""
        if self._initialized or not HAS_PADDLE:
            return
        try:
            logger.info("Initializing PaddleOCR...")
            # det_db_thresh: 检测阈值，低门槛召回更多文字区域
            # rec: 启用文字识别
            # cls: 启用方向分类
            self._ocr = PaddleOCRClient(
                use_angle_cls=True,
                lang="ch",
                det_db_thresh=0.3,
                use_gpu=False,
                show_log=False,
            )
            self._initialized = True
            logger.info("PaddleOCR initialized successfully")
        except Exception as e:
            logger.error(f"PaddleOCR init failed: {e}")
            self._initialized = True  # 防止重复初始化

    async def recognize(self, image_path: str | Path) -> OCRResult:
        """
        识别图片中的文字
        支持：扫描件、截图、照片
        """
        path = Path(image_path)
        if not path.exists():
            return OCRResult(text=f"[文件不存在: {image_path}]")

        # 如果 PaddleOCR 不可用，返回占位信息
        if not HAS_PADDLE:
            # 尝试用 PIL 读取基本信息
            if HAS_PIL:
                try:
                    img = Image.open(path)
                    return OCRResult(
                        text=f"[图片文件: {path.name}] ({img.width}x{img.height}) OCR 引擎未安装",
                        paragraphs=[{
                            "text": f"图片: {path.name} ({img.width}x{img.height})",
                            "confidence": 0,
                        }],
                    )
                except Exception:
                    pass
            return OCRResult(
                text=f"[图片文件: {path.name}] OCR 引擎未安装，请安装 PaddleOCR",
            )

        self._ensure_initialized()
        if self._ocr is None:
            return OCRResult(text=f"[图片: {path.name}] OCR 初始化失败")

        try:
            result = self._ocr.ocr(str(path), cls=True)
            if not result or not result[0]:
                return OCRResult(text=f"[图片: {path.name}] 未识别到文字")

            paragraphs = []
            lines = []
            for line_info in result[0]:
                # line_info: [bbox, (text, confidence)]
                if len(line_info) < 2:
                    continue
                bbox, (text, confidence) = line_info
                paragraphs.append({
                    "text": text,
                    "confidence": float(confidence),
                    "bbox": [float(x) for point in bbox for x in point],
                })
                lines.append(text)

            full_text = "\n".join(lines)
            logger.info(f"OCR recognized: {path.name} -> {len(lines)} lines")
            return OCRResult(text=full_text, paragraphs=paragraphs)

        except Exception as e:
            logger.error(f"OCR error: {e}")
            return OCRResult(text=f"[图片: {path.name}] OCR 识别失败: {str(e)[:100]}")


ocr_service = OCRService()
