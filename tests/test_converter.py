import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.converter import ConversionResult, DocumentConverter


class TestDocumentConverter:
    """Test suite for DocumentConverter"""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def converter(self, temp_dir):
        """Create a converter instance"""
        return DocumentConverter(output_dir=temp_dir)

    def test_get_output_paths_with_output_dir(self, converter, temp_dir):
        """Test output path generation with output directory"""
        input_path = Path("/some/path/document.pdf")
        md_path, json_path = converter._get_output_paths(input_path)

        assert md_path.suffix == ".md"
        assert json_path.suffix == ".json"
        assert md_path.parent == json_path.parent
        assert str(temp_dir) in str(md_path)

    def test_get_output_paths_without_output_dir(self):
        """Test output path generation without output directory"""
        converter = DocumentConverter()
        input_path = Path("/some/path/document.pdf")
        md_path, json_path = converter._get_output_paths(input_path)

        assert md_path == Path("/some/path/document.md")
        assert json_path == Path("/some/path/document.json")

    def test_find_documents_single_file(self, converter, temp_dir):
        """Test finding documents with single file"""
        test_file = temp_dir / "test.pdf"
        test_file.touch()

        documents = converter.find_documents(test_file)
        assert len(documents) == 1
        assert documents[0] == test_file

    def test_find_documents_directory(self, converter, temp_dir):
        """Test finding documents in directory"""
        # Create test files
        (temp_dir / "doc1.pdf").touch()
        (temp_dir / "doc2.docx").touch()
        (temp_dir / "doc3.pptx").touch()
        (temp_dir / "ignore.txt").touch()

        subdir = temp_dir / "subdir"
        subdir.mkdir()
        (subdir / "doc4.pdf").touch()

        documents = converter.find_documents(temp_dir)
        assert len(documents) == 4
        assert all(doc.suffix in [".pdf", ".docx", ".pptx"] for doc in documents)

    @patch("src.converter.text_from_rendered")
    @patch("src.converter.PdfConverter")
    @patch("src.converter.create_model_dict")
    def test_convert_pdf_success(
        self, mock_create_model_dict, mock_pdf_converter_class, mock_text_from_rendered, converter, temp_dir
    ):
        """Test successful PDF conversion"""
        # Setup mocks
        mock_create_model_dict.return_value = {}
        mock_pdf_converter = Mock()
        mock_pdf_converter_class.return_value = mock_pdf_converter
        mock_pdf_converter.return_value = Mock()  # rendered object
        mock_text_from_rendered.return_value = ("# Test Content\nThis is test content.", None, [])

        # Create test PDF
        test_pdf = temp_dir / "test.pdf"
        test_pdf.touch()

        # Convert
        result = converter.convert_pdf(test_pdf)

        # Verify
        assert result.status == "success"
        assert result.error is None
        assert Path(result.markdown_path).exists()
        assert Path(result.json_path).exists()

        # Check content
        md_content = Path(result.markdown_path).read_text()
        assert "# Test Content" in md_content

        json_content = json.loads(Path(result.json_path).read_text())
        assert json_content["type"] == "pdf"
        assert json_content["content"] == "# Test Content\nThis is test content."

    @patch("src.converter.PdfConverter")
    @patch("src.converter.create_model_dict")
    def test_convert_pdf_error(self, mock_create_model_dict, mock_pdf_converter_class, converter, temp_dir):
        """Test PDF conversion error handling"""
        mock_create_model_dict.return_value = {}
        mock_pdf_converter_class.side_effect = Exception("PDF conversion failed")

        test_pdf = temp_dir / "test.pdf"
        test_pdf.touch()

        result = converter.convert_pdf(test_pdf)

        assert result.status == "error"
        assert "PDF conversion failed" in result.error
        assert result.markdown_path == ""
        assert result.json_path == ""

    @patch("src.converter.Document")
    def test_convert_docx_success(self, mock_document_class, converter, temp_dir):
        """Test successful DOCX conversion"""
        # Setup mock document
        mock_doc = Mock()
        mock_document_class.return_value = mock_doc

        # Mock paragraphs
        para1 = Mock()
        para1.text = "Test Title"
        para1.style.name = "Heading 1"
        para1.runs = []

        para2 = Mock()
        para2.text = "Normal text"
        para2.style.name = "Normal"
        para2.runs = []

        mock_doc.paragraphs = [para1, para2]

        # Mock properties
        mock_doc.core_properties.author = "Test Author"
        mock_doc.core_properties.title = "Test Title"
        mock_doc.core_properties.created = None
        mock_doc.core_properties.modified = None

        # Create test file
        test_docx = temp_dir / "test.docx"
        test_docx.touch()

        # Convert
        result = converter.convert_docx(test_docx)

        # Verify
        assert result.status == "success"
        assert Path(result.markdown_path).exists()

        md_content = Path(result.markdown_path).read_text()
        assert "# Test Title" in md_content
        assert "Normal text" in md_content

    @patch("src.converter.Presentation")
    def test_convert_pptx_success(self, mock_presentation_class, converter, temp_dir):
        """Test successful PPTX conversion"""
        # Setup mock presentation
        mock_prs = Mock()
        mock_presentation_class.return_value = mock_prs

        # Mock slide
        mock_slide = Mock()
        mock_shape = Mock()
        mock_shape.text = "Slide Title"

        # Create a mock shapes collection
        mock_shapes = Mock()
        mock_shapes.__iter__ = Mock(return_value=iter([mock_shape]))
        mock_shapes.title = mock_shape

        mock_slide.shapes = mock_shapes
        mock_slide.has_notes_slide = False

        mock_prs.slides = [mock_slide]

        # Mock properties
        mock_prs.core_properties.title = "Test Presentation"
        mock_prs.core_properties.author = "Test Author"
        mock_prs.core_properties.created = None
        mock_prs.core_properties.modified = None

        # Create test file
        test_pptx = temp_dir / "test.pptx"
        test_pptx.touch()

        # Convert
        result = converter.convert_pptx(test_pptx)

        # Verify
        assert result.status == "success"
        assert Path(result.markdown_path).exists()

        md_content = Path(result.markdown_path).read_text()
        assert "# Slide 1" in md_content
        assert "## Slide Title" in md_content

    def test_convert_document_unsupported(self, converter, temp_dir):
        """Test converting unsupported document type"""
        test_file = temp_dir / "test.txt"
        test_file.touch()

        result = converter.convert_document(test_file)

        assert result.status == "error"
        assert "Unsupported file type" in result.error

    @patch("src.converter.DocumentConverter.convert_pdf")
    @patch("src.converter.DocumentConverter.convert_docx")
    @patch("src.converter.DocumentConverter.convert_pptx")
    def test_convert_all(self, mock_pptx, mock_docx, mock_pdf, converter, temp_dir):
        """Test converting multiple documents"""
        # Create test files
        (temp_dir / "test1.pdf").touch()
        (temp_dir / "test2.docx").touch()
        (temp_dir / "test3.pptx").touch()

        # Setup mocks to return success
        mock_pdf.return_value = ConversionResult(
            source_path="test1.pdf", markdown_path="test1.md", json_path="test1.json", status="success"
        )
        mock_docx.return_value = ConversionResult(
            source_path="test2.docx", markdown_path="test2.md", json_path="test2.json", status="success"
        )
        mock_pptx.return_value = ConversionResult(
            source_path="test3.pptx", markdown_path="test3.md", json_path="test3.json", status="success"
        )

        # Convert all
        results = converter.convert_all(temp_dir)

        # Verify
        assert len(results) == 3
        assert all(r.status == "success" for r in results)
        assert mock_pdf.called
        assert mock_docx.called
        assert mock_pptx.called


class TestConversionResult:
    """Test ConversionResult dataclass"""

    def test_conversion_result_creation(self):
        """Test creating ConversionResult"""
        result = ConversionResult(
            source_path="/path/to/doc.pdf",
            markdown_path="/path/to/doc.md",
            json_path="/path/to/doc.json",
            status="success",
            metadata={"pages": 10},
        )

        assert result.source_path == "/path/to/doc.pdf"
        assert result.status == "success"
        assert result.error is None
        assert result.metadata["pages"] == 10

    def test_conversion_result_error(self):
        """Test ConversionResult with error"""
        result = ConversionResult(
            source_path="/path/to/doc.pdf", markdown_path="", json_path="", status="error", error="Failed to convert"
        )

        assert result.status == "error"
        assert result.error == "Failed to convert"
        assert result.markdown_path == ""


class TestFolderStructurePreservation:
    """Test that folder structure is preserved when converting directories"""

    @pytest.fixture
    def nested_temp_dir(self):
        """Create a nested directory structure for testing"""
        temp_dir = tempfile.mkdtemp()
        base_path = Path(temp_dir)

        # Create nested structure
        (base_path / "level1").mkdir()
        (base_path / "level1" / "level2").mkdir()
        (base_path / "level1" / "level2" / "level3").mkdir()

        yield base_path
        shutil.rmtree(temp_dir)

    def test_output_paths_preserve_structure_with_base_dir(self, nested_temp_dir):
        """Test that output paths preserve folder structure when base_input_path is set"""
        output_dir = nested_temp_dir / "output"
        converter = DocumentConverter(output_dir=output_dir, base_input_path=nested_temp_dir)

        # Test file in nested directory
        input_file = nested_temp_dir / "level1" / "level2" / "test.pdf"
        md_path, json_path = converter._get_output_paths(input_file)

        # Should preserve the relative structure
        assert md_path == output_dir / "level1" / "level2" / "test.md"
        assert json_path == output_dir / "level1" / "level2" / "test.json"

    def test_output_paths_single_file_no_structure(self, nested_temp_dir):
        """Test that single files don't preserve structure"""
        output_dir = nested_temp_dir / "output"
        converter = DocumentConverter(
            output_dir=output_dir,
            base_input_path=None,  # No base path for single file
        )

        # Test single file
        input_file = nested_temp_dir / "level1" / "level2" / "test.pdf"
        md_path, json_path = converter._get_output_paths(input_file)

        # Should NOT preserve structure, just use filename
        assert md_path == output_dir / "test.md"
        assert json_path == output_dir / "test.json"

    @patch("src.converter.Document")
    def test_convert_preserves_nested_structure(self, mock_document_class, nested_temp_dir):
        """Test that actual conversion preserves nested directory structure"""
        output_dir = nested_temp_dir / "output"
        converter = DocumentConverter(output_dir=output_dir, base_input_path=nested_temp_dir)

        # Setup mock document
        mock_doc = Mock()
        mock_document_class.return_value = mock_doc
        mock_doc.paragraphs = []
        mock_doc.core_properties.author = ""
        mock_doc.core_properties.title = ""
        mock_doc.core_properties.created = None
        mock_doc.core_properties.modified = None

        # Create test file in nested directory
        test_file = nested_temp_dir / "level1" / "level2" / "level3" / "deep.docx"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.touch()

        # Convert
        result = converter.convert_docx(test_file)

        # Check that output preserves structure
        assert result.status == "success"
        expected_md = output_dir / "level1" / "level2" / "level3" / "deep.md"
        expected_json = output_dir / "level1" / "level2" / "level3" / "deep.json"

        assert result.markdown_path == str(expected_md)
        assert result.json_path == str(expected_json)
        assert expected_md.exists()
        assert expected_json.exists()

        # Verify parent directories were created
        assert (output_dir / "level1").is_dir()
        assert (output_dir / "level1" / "level2").is_dir()
        assert (output_dir / "level1" / "level2" / "level3").is_dir()

    def test_files_outside_base_path_use_flat_structure(self, nested_temp_dir):
        """Test files outside base path fall back to flat structure"""
        output_dir = nested_temp_dir / "output"
        base_dir = nested_temp_dir / "base"
        base_dir.mkdir()

        converter = DocumentConverter(output_dir=output_dir, base_input_path=base_dir)

        # File outside base directory
        outside_file = nested_temp_dir / "outside.pdf"
        md_path, json_path = converter._get_output_paths(outside_file)

        # Should use flat structure since file is outside base path
        assert md_path == output_dir / "outside.md"
        assert json_path == output_dir / "outside.json"
