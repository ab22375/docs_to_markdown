"""OCR module for handling scanned PDFs using Surya"""

import logging
from pathlib import Path
from typing import List, Optional, Tuple

import torch
from PIL import Image
from surya.detection import DetectionPredictor
from surya.recognition import RecognitionPredictor

logger = logging.getLogger(__name__)


class SuryaOCRProcessor:
    """Surya OCR processor for scanned PDFs"""

    def __init__(self, device: Optional[torch.device] = None):
        # Force CPU for now to avoid MPS issues on macOS with Surya
        if device is None:
            if torch.cuda.is_available():
                self.device = torch.device("cuda")
            else:
                # Avoid MPS on macOS due to compatibility issues with Surya
                self.device = torch.device("cpu")
        else:
            self.device = device
        self._models_loaded = False
        self.detection_predictor = None
        self.recognition_predictor = None

    def _load_models(self):
        """Lazy load Surya models"""
        if not self._models_loaded:
            try:
                logger.info("Loading Surya OCR models...")
                # Set environment variable to force CPU usage if needed
                import os
                if self.device.type == "cpu":
                    os.environ["PYTORCH_DEVICE"] = "cpu"
                
                self.detection_predictor = DetectionPredictor()
                self.recognition_predictor = RecognitionPredictor()
                self._models_loaded = True
                logger.info(f"Surya OCR models loaded successfully on {self.device}")
            except Exception as e:
                logger.error(f"Failed to load Surya OCR models: {e}")
                raise RuntimeError(f"OCR model loading failed: {e}")

    def is_scanned_pdf(self, pdf_path: Path, sample_pages: int = 3) -> bool:
        """
        Detect if a PDF is scanned (image-based) or contains extractable text.

        Args:
            pdf_path: Path to the PDF file
            sample_pages: Number of pages to sample for detection

        Returns:
            True if the PDF appears to be scanned, False otherwise
        """
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(str(pdf_path))
            total_pages = min(len(doc), sample_pages)

            if total_pages == 0:
                return False

            text_chars = 0
            image_count = 0

            for i in range(total_pages):
                page = doc[i]
                text = page.get_text().strip()
                text_chars += len(text)

                # Count images on the page
                image_list = page.get_images()
                image_count += len(image_list)

            doc.close()

            # Heuristic: If average text per page is very low but images exist,
            # it's likely a scanned PDF
            avg_text_per_page = text_chars / total_pages
            avg_images_per_page = image_count / total_pages

            is_scanned = avg_text_per_page < 100 and avg_images_per_page >= 0.8

            if is_scanned:
                logger.info(f"Detected scanned PDF: {pdf_path} (avg text: {avg_text_per_page:.1f} chars/page)")

            return is_scanned

        except Exception as e:
            logger.warning(f"Error detecting if PDF is scanned: {e}")
            return False

    def extract_images_from_pdf(self, pdf_path: Path) -> List[Image.Image]:
        """Extract images from PDF pages"""
        try:
            import fitz

            doc = fitz.open(str(pdf_path))
            images = []

            for page_num in range(len(doc)):
                page = doc[page_num]
                # Render page as image
                mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img_data = pix.tobytes("png")

                # Convert to PIL Image
                import io

                img = Image.open(io.BytesIO(img_data))
                images.append(img)

            doc.close()
            return images

        except Exception as e:
            logger.error(f"Error extracting images from PDF: {e}")
            return []

    def process_with_ocr(self, pdf_path: Path, langs: Optional[List[str]] = None) -> Tuple[str, dict]:
        """
        Process a scanned PDF with Surya OCR.

        Args:
            pdf_path: Path to the PDF file
            langs: List of language codes (unused in current Surya API but kept for compatibility)

        Returns:
            Tuple of (extracted_text, metadata)
        """
        try:
            self._load_models()

            if langs is None:
                langs = ["en"]

            logger.info(f"Processing {pdf_path} with Surya OCR")

            # Extract images from PDF
            images = self.extract_images_from_pdf(pdf_path)
            if not images:
                return "", {"error": "No images could be extracted from PDF"}

            # Run OCR on all pages using Surya
            predictions = self.recognition_predictor(images, det_predictor=self.detection_predictor)

            # Combine text from all pages
            full_text = []
            page_texts = []

            for page_num, prediction in enumerate(predictions):
                page_text = []

                # Extract text from prediction
                if hasattr(prediction, "text_lines"):
                    # Sort text lines by vertical position for better reading order
                    sorted_lines = sorted(
                        prediction.text_lines,
                        key=lambda x: (x.bbox[1], x.bbox[0]),  # Sort by y, then x
                    )

                    for line in sorted_lines:
                        if hasattr(line, "text") and line.text.strip():
                            page_text.append(line.text)
                elif hasattr(prediction, "text"):
                    # Direct text attribute
                    page_text = [prediction.text] if prediction.text.strip() else []

                page_content = "\n".join(page_text)
                page_texts.append(page_content)
                full_text.append(f"## Page {page_num + 1}\n\n{page_content}")

            combined_text = "\n\n".join(full_text)

            metadata = {
                "ocr_used": True,
                "ocr_engine": "surya",
                "languages": langs,
                "page_count": len(images),
                "page_texts": page_texts,
            }

            logger.info(f"OCR completed for {pdf_path}: {len(images)} pages processed")

            return combined_text, metadata
            
        except Exception as e:
            logger.error(f"OCR processing failed for {pdf_path}: {e}")
            # Return error information instead of raising
            return "", {"error": f"OCR processing failed: {str(e)}"}


class OCRPlugin:
    """Base class for OCR plugins"""

    def __init__(self, device: Optional[torch.device] = None):
        self.device = device

    def is_supported(self, file_path: Path) -> bool:
        """Check if this plugin can handle the file"""
        raise NotImplementedError

    def process(self, file_path: Path, **kwargs) -> Tuple[str, dict]:
        """Process the file and return extracted text and metadata"""
        raise NotImplementedError


class SuryaOCRPlugin(OCRPlugin):
    """Surya OCR plugin implementation"""

    def __init__(self, device: Optional[torch.device] = None):
        super().__init__(device)
        self.processor = SuryaOCRProcessor(device)

    def is_supported(self, file_path: Path) -> bool:
        """Check if file is a scanned PDF"""
        return file_path.suffix.lower() == ".pdf" and self.processor.is_scanned_pdf(file_path)

    def process(self, file_path: Path, **kwargs) -> Tuple[str, dict]:
        """Process scanned PDF with OCR"""
        langs = kwargs.get("languages", ["en"])
        return self.processor.process_with_ocr(file_path, langs)


class OCRManager:
    """Manager for OCR plugins"""

    def __init__(self, device: Optional[torch.device] = None, enable_ocr: bool = True):
        self.device = device
        self.plugins: List[OCRPlugin] = []
        self.enable_ocr = enable_ocr
        if enable_ocr:
            self._register_default_plugins()

    def _register_default_plugins(self):
        """Register default OCR plugins"""
        self.register_plugin(SuryaOCRPlugin(self.device))

    def register_plugin(self, plugin: OCRPlugin):
        """Register a new OCR plugin"""
        self.plugins.append(plugin)

    def process_if_needed(self, file_path: Path, **kwargs) -> Optional[Tuple[str, dict]]:
        """
        Process file with OCR if needed.

        Returns:
            Tuple of (text, metadata) if OCR was used, None otherwise
        """
        if not self.enable_ocr:
            return None
            
        for plugin in self.plugins:
            try:
                if plugin.is_supported(file_path):
                    logger.info(f"Using {plugin.__class__.__name__} for {file_path}")
                    result = plugin.process(file_path, **kwargs)
                    # Check if OCR failed and returned an error
                    if result and len(result) == 2:
                        text, metadata = result
                        if metadata.get("error"):
                            logger.warning(f"OCR processing failed for {file_path}: {metadata['error']}")
                            continue  # Try next plugin or fall back to regular processing
                    return result
            except Exception as e:
                logger.warning(f"OCR plugin {plugin.__class__.__name__} failed for {file_path}: {e}")
                continue  # Try next plugin or fall back to regular processing

        return None
