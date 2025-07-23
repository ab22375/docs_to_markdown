"""Tests for OCR functionality"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from PIL import Image

from src.ocr import (
    OCRManager,
    OCRPlugin,
    SuryaOCRPlugin,
    SuryaOCRProcessor,
)


class TestSuryaOCRProcessor:
    """Test suite for SuryaOCRProcessor"""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def processor(self):
        """Create a processor instance"""
        with patch("torch.device"):
            return SuryaOCRProcessor()

    @pytest.fixture
    def mock_pdf_path(self, temp_dir):
        """Create a mock PDF file"""
        pdf_path = temp_dir / "test.pdf"
        pdf_path.touch()
        return pdf_path

    def test_init(self, processor):
        """Test processor initialization"""
        assert processor.device is not None
        assert not processor._models_loaded
        assert processor.detection_predictor is None
        assert processor.recognition_predictor is None

    @patch("src.ocr.DetectionPredictor")
    @patch("src.ocr.RecognitionPredictor")
    def test_load_models(self, mock_rec_predictor, mock_det_predictor, processor):
        """Test model loading"""
        # Mock return values
        mock_det_predictor.return_value = Mock()
        mock_rec_predictor.return_value = Mock()

        processor._load_models()

        assert processor._models_loaded
        assert processor.detection_predictor is not None
        assert processor.recognition_predictor is not None

    @patch("fitz.open")
    def test_is_scanned_pdf_true(self, mock_fitz_open, processor, mock_pdf_path):
        """Test detection of scanned PDF"""
        # Mock PDF document
        mock_doc = MagicMock()
        mock_page = Mock()
        mock_page.get_text.return_value = "a"  # Very little text
        mock_page.get_images.return_value = [Mock(), Mock()]  # Multiple images
        mock_doc.__len__ = Mock(return_value=1)
        mock_doc.__getitem__ = Mock(return_value=mock_page)
        mock_fitz_open.return_value = mock_doc

        result = processor.is_scanned_pdf(mock_pdf_path)

        assert result is True
        mock_doc.close.assert_called_once()

    @patch("fitz.open")
    def test_is_scanned_pdf_false(self, mock_fitz_open, processor, mock_pdf_path):
        """Test detection of text-based PDF"""
        # Mock PDF document
        mock_doc = MagicMock()
        mock_page = Mock()
        mock_page.get_text.return_value = "This is a lot of text content that indicates a text-based PDF document"
        mock_page.get_images.return_value = []  # No images
        mock_doc.__len__ = Mock(return_value=1)
        mock_doc.__getitem__ = Mock(return_value=mock_page)
        mock_fitz_open.return_value = mock_doc

        result = processor.is_scanned_pdf(mock_pdf_path)

        assert result is False
        mock_doc.close.assert_called_once()

    @patch("fitz.open")
    def test_is_scanned_pdf_error_handling(self, mock_fitz_open, processor, mock_pdf_path):
        """Test error handling in PDF detection"""
        mock_fitz_open.side_effect = Exception("PDF error")

        result = processor.is_scanned_pdf(mock_pdf_path)

        assert result is False

    @patch("fitz.open")
    @patch("io.BytesIO")
    @patch("PIL.Image.open")
    def test_extract_images_from_pdf(self, mock_pil_open, mock_bytesio, mock_fitz_open, processor, mock_pdf_path):
        """Test image extraction from PDF"""
        # Mock PDF document
        mock_doc = MagicMock()
        mock_page = Mock()
        mock_pixmap = Mock()
        mock_pixmap.tobytes.return_value = b"mock_image_data"
        mock_page.get_pixmap.return_value = mock_pixmap
        mock_doc.__len__ = Mock(return_value=2)
        mock_doc.__getitem__ = Mock(return_value=mock_page)
        mock_fitz_open.return_value = mock_doc

        # Mock PIL Image
        mock_image = Mock(spec=Image.Image)
        mock_pil_open.return_value = mock_image

        result = processor.extract_images_from_pdf(mock_pdf_path)

        assert len(result) == 2
        assert all(isinstance(img, Mock) for img in result)
        mock_doc.close.assert_called_once()

    @patch("fitz.open")
    def test_extract_images_from_pdf_error(self, mock_fitz_open, processor, mock_pdf_path):
        """Test error handling in image extraction"""
        mock_fitz_open.side_effect = Exception("PDF error")

        result = processor.extract_images_from_pdf(mock_pdf_path)

        assert result == []

    @patch.object(SuryaOCRProcessor, "_load_models")
    @patch.object(SuryaOCRProcessor, "extract_images_from_pdf")
    def test_process_with_ocr(self, mock_extract_images, mock_load_models, processor, mock_pdf_path):
        """Test OCR processing"""
        # Mock images
        mock_images = [Mock(spec=Image.Image), Mock(spec=Image.Image)]
        mock_extract_images.return_value = mock_images

        # Mock OCR predictions
        mock_line1 = Mock()
        mock_line1.text = "Line 1 text"
        mock_line1.bbox = [0, 0, 100, 20]

        mock_line2 = Mock()
        mock_line2.text = "Line 2 text"
        mock_line2.bbox = [0, 25, 100, 45]

        mock_prediction = Mock()
        mock_prediction.text_lines = [mock_line1, mock_line2]

        # Mock recognition predictor
        processor.recognition_predictor = Mock()
        processor.recognition_predictor.return_value = [mock_prediction, mock_prediction]
        processor.detection_predictor = Mock()

        result_text, metadata = processor.process_with_ocr(mock_pdf_path, ["en"])

        assert "## Page 1" in result_text
        assert "## Page 2" in result_text
        assert "Line 1 text" in result_text
        assert "Line 2 text" in result_text
        assert metadata["ocr_used"] is True
        assert metadata["ocr_engine"] == "surya"
        assert metadata["languages"] == ["en"]
        assert metadata["page_count"] == 2

    @patch.object(SuryaOCRProcessor, "extract_images_from_pdf")
    def test_process_with_ocr_no_images(self, mock_extract_images, processor, mock_pdf_path):
        """Test OCR processing when no images are extracted"""
        mock_extract_images.return_value = []

        result_text, metadata = processor.process_with_ocr(mock_pdf_path)

        assert result_text == ""
        assert "error" in metadata


class TestSuryaOCRPlugin:
    """Test suite for SuryaOCRPlugin"""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def plugin(self):
        """Create a plugin instance"""
        with patch("torch.device"):
            return SuryaOCRPlugin()

    @pytest.fixture
    def mock_pdf_path(self, temp_dir):
        """Create a mock PDF file"""
        pdf_path = temp_dir / "test.pdf"
        pdf_path.touch()
        return pdf_path

    @pytest.fixture
    def mock_txt_path(self, temp_dir):
        """Create a mock text file"""
        txt_path = temp_dir / "test.txt"
        txt_path.touch()
        return txt_path

    @patch.object(SuryaOCRProcessor, "is_scanned_pdf")
    def test_is_supported_scanned_pdf(self, mock_is_scanned, plugin, mock_pdf_path):
        """Test plugin support for scanned PDF"""
        mock_is_scanned.return_value = True

        result = plugin.is_supported(mock_pdf_path)

        assert result is True

    @patch.object(SuryaOCRProcessor, "is_scanned_pdf")
    def test_is_supported_text_pdf(self, mock_is_scanned, plugin, mock_pdf_path):
        """Test plugin support for text-based PDF"""
        mock_is_scanned.return_value = False

        result = plugin.is_supported(mock_pdf_path)

        assert result is False

    def test_is_supported_non_pdf(self, plugin, mock_txt_path):
        """Test plugin support for non-PDF file"""
        result = plugin.is_supported(mock_txt_path)

        assert result is False

    @patch.object(SuryaOCRProcessor, "process_with_ocr")
    def test_process(self, mock_process_ocr, plugin, mock_pdf_path):
        """Test plugin processing"""
        mock_process_ocr.return_value = ("extracted text", {"ocr_used": True})

        result_text, metadata = plugin.process(mock_pdf_path, languages=["en", "es"])

        assert result_text == "extracted text"
        assert metadata["ocr_used"] is True
        mock_process_ocr.assert_called_once_with(mock_pdf_path, ["en", "es"])


class TestOCRManager:
    """Test suite for OCRManager"""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def manager(self):
        """Create a manager instance"""
        with patch("torch.device"):
            return OCRManager()

    @pytest.fixture
    def mock_pdf_path(self, temp_dir):
        """Create a mock PDF file"""
        pdf_path = temp_dir / "test.pdf"
        pdf_path.touch()
        return pdf_path

    def test_init(self, manager):
        """Test manager initialization"""
        assert len(manager.plugins) == 1
        assert isinstance(manager.plugins[0], SuryaOCRPlugin)

    def test_register_plugin(self, manager):
        """Test plugin registration"""
        mock_plugin = Mock(spec=OCRPlugin)

        manager.register_plugin(mock_plugin)

        assert len(manager.plugins) == 2
        assert mock_plugin in manager.plugins

    def test_process_if_needed_supported(self, manager, mock_pdf_path):
        """Test processing when file is supported"""
        mock_plugin = Mock(spec=OCRPlugin)
        mock_plugin.is_supported.return_value = True
        mock_plugin.process.return_value = ("text", {"meta": "data"})

        manager.plugins = [mock_plugin]

        result = manager.process_if_needed(mock_pdf_path)

        assert result == ("text", {"meta": "data"})
        mock_plugin.is_supported.assert_called_once_with(mock_pdf_path)
        mock_plugin.process.assert_called_once_with(mock_pdf_path)

    def test_process_if_needed_not_supported(self, manager, mock_pdf_path):
        """Test processing when file is not supported"""
        mock_plugin = Mock(spec=OCRPlugin)
        mock_plugin.is_supported.return_value = False

        manager.plugins = [mock_plugin]

        result = manager.process_if_needed(mock_pdf_path)

        assert result is None
        mock_plugin.is_supported.assert_called_once_with(mock_pdf_path)
        mock_plugin.process.assert_not_called()

    def test_process_if_needed_multiple_plugins(self, manager, mock_pdf_path):
        """Test processing with multiple plugins"""
        mock_plugin1 = Mock(spec=OCRPlugin)
        mock_plugin1.is_supported.return_value = False

        mock_plugin2 = Mock(spec=OCRPlugin)
        mock_plugin2.is_supported.return_value = True
        mock_plugin2.process.return_value = ("text", {"meta": "data"})

        manager.plugins = [mock_plugin1, mock_plugin2]

        result = manager.process_if_needed(mock_pdf_path)

        assert result == ("text", {"meta": "data"})
        mock_plugin1.is_supported.assert_called_once_with(mock_pdf_path)
        mock_plugin2.is_supported.assert_called_once_with(mock_pdf_path)
        mock_plugin2.process.assert_called_once_with(mock_pdf_path)


class MockOCRPlugin(OCRPlugin):
    """Mock OCR plugin for testing"""

    def __init__(self, supported=True, result=("mock text", {"mock": "metadata"})):
        super().__init__()
        self.supported = supported
        self.result = result

    def is_supported(self, file_path: Path) -> bool:
        return self.supported

    def process(self, file_path: Path, **kwargs) -> tuple:
        return self.result


class TestOCRIntegration:
    """Integration tests for OCR functionality"""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    def test_custom_plugin_registration(self, temp_dir):
        """Test registering and using custom OCR plugin"""
        with patch("torch.device"):
            manager = OCRManager()

        # Create custom plugin
        custom_plugin = MockOCRPlugin(supported=True, result=("custom text", {"custom": True}))
        manager.register_plugin(custom_plugin)

        # Test file
        test_file = temp_dir / "test.pdf"
        test_file.touch()

        # Process should use the first plugin that supports the file
        result = manager.process_if_needed(test_file)

        # Since SuryaOCRPlugin is registered first, it should be tried first
        # But our MockOCRPlugin will be tried if Surya doesn't support it
        assert result is not None
