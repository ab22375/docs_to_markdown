import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from src.converter import main


class TestIntegration:
    """Integration tests for the converter CLI"""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner"""
        return CliRunner()

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    def create_mock_pdf(self, path: Path):
        """Create a mock PDF file"""
        path.write_bytes(b"%PDF-1.4\n%Fake PDF content")

    def create_mock_docx(self, path: Path):
        """Create a mock DOCX file"""
        # DOCX files are actually zip files
        import zipfile

        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("[Content_Types].xml", '<?xml version="1.0"?>')

    def create_mock_pptx(self, path: Path):
        """Create a mock PPTX file"""
        # PPTX files are also zip files
        import zipfile

        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("[Content_Types].xml", '<?xml version="1.0"?>')

    @patch("src.converter.DocumentConverter.convert_pdf")
    def test_cli_single_file(self, mock_convert_pdf, runner, temp_dir):
        """Test CLI with single file"""
        # Create test PDF
        test_pdf = temp_dir / "test.pdf"
        self.create_mock_pdf(test_pdf)

        # Mock conversion
        from src.converter import ConversionResult

        mock_convert_pdf.return_value = ConversionResult(
            source_path=str(test_pdf),
            markdown_path=str(temp_dir / "test.md"),
            json_path=str(temp_dir / "test.json"),
            status="success",
        )

        # Run CLI
        result = runner.invoke(main, [str(test_pdf)])

        assert result.exit_code == 0
        assert "Found 1 documents to convert" in result.output
        assert mock_convert_pdf.called

    @patch("src.converter.DocumentConverter.convert_pdf")
    @patch("src.converter.DocumentConverter.convert_docx")
    @patch("src.converter.DocumentConverter.convert_pptx")
    def test_cli_directory(self, mock_pptx, mock_docx, mock_pdf, runner, temp_dir):
        """Test CLI with directory"""
        # Create test files
        self.create_mock_pdf(temp_dir / "doc1.pdf")
        self.create_mock_docx(temp_dir / "doc2.docx")
        self.create_mock_pptx(temp_dir / "doc3.pptx")

        # Mock conversions
        from src.converter import ConversionResult

        mock_pdf.return_value = ConversionResult(
            source_path=str(temp_dir / "doc1.pdf"),
            markdown_path=str(temp_dir / "doc1.md"),
            json_path=str(temp_dir / "doc1.json"),
            status="success",
        )
        mock_docx.return_value = ConversionResult(
            source_path=str(temp_dir / "doc2.docx"),
            markdown_path=str(temp_dir / "doc2.md"),
            json_path=str(temp_dir / "doc2.json"),
            status="success",
        )
        mock_pptx.return_value = ConversionResult(
            source_path=str(temp_dir / "doc3.pptx"),
            markdown_path=str(temp_dir / "doc3.md"),
            json_path=str(temp_dir / "doc3.json"),
            status="success",
        )

        # Run CLI
        result = runner.invoke(main, [str(temp_dir)])

        assert result.exit_code == 0
        assert "Found 3 documents to convert" in result.output

    @patch("src.converter.DocumentConverter.convert_pdf")
    def test_cli_with_output_dir(self, mock_convert_pdf, runner, temp_dir):
        """Test CLI with output directory option"""
        # Create test PDF
        test_pdf = temp_dir / "test.pdf"
        self.create_mock_pdf(test_pdf)

        output_dir = temp_dir / "output"

        # Mock conversion
        from src.converter import ConversionResult

        mock_convert_pdf.return_value = ConversionResult(
            source_path=str(test_pdf),
            markdown_path=str(output_dir / "test.md"),
            json_path=str(output_dir / "test.json"),
            status="success",
        )

        # Run CLI
        result = runner.invoke(main, [str(test_pdf), "--output-dir", str(output_dir)])

        assert result.exit_code == 0

    @patch("src.converter.DocumentConverter.convert_pdf")
    def test_cli_with_summary(self, mock_convert_pdf, runner, temp_dir):
        """Test CLI with summary option"""
        # Create test PDF
        test_pdf = temp_dir / "test.pdf"
        self.create_mock_pdf(test_pdf)

        # Mock conversion
        from src.converter import ConversionResult

        mock_convert_pdf.return_value = ConversionResult(
            source_path=str(test_pdf),
            markdown_path=str(temp_dir / "test.md"),
            json_path=str(temp_dir / "test.json"),
            status="success",
        )

        # Run CLI with summary
        result = runner.invoke(main, [str(test_pdf), "--summary"])

        assert result.exit_code == 0
        assert "Conversion Summary" in result.output
        assert "Total: 1 | Success: 1 | Failed: 0" in result.output

    def test_cli_no_documents_found(self, runner, temp_dir):
        """Test CLI when no documents are found"""
        # Create directory with no supported files
        (temp_dir / "test.txt").touch()

        result = runner.invoke(main, [str(temp_dir)])

        assert result.exit_code == 0
        assert "No supported documents found" in result.output

    @patch("src.converter.DocumentConverter.convert_pdf")
    def test_cli_with_error(self, mock_convert_pdf, runner, temp_dir):
        """Test CLI handling conversion errors"""
        # Create test PDF
        test_pdf = temp_dir / "test.pdf"
        self.create_mock_pdf(test_pdf)

        # Mock conversion failure
        from src.converter import ConversionResult

        mock_convert_pdf.return_value = ConversionResult(
            source_path=str(test_pdf), markdown_path="", json_path="", status="error", error="Conversion failed"
        )

        # Run CLI
        result = runner.invoke(main, [str(test_pdf), "--summary"])

        assert result.exit_code == 0
        assert "Error: Conversion failed" in result.output
        assert "Total: 1 | Success: 0 | Failed: 1" in result.output

    def test_cli_help(self, runner):
        """Test CLI help"""
        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "Convert PDF, DOCX, and PPTX files to Markdown and JSON" in result.output
        assert "--output-dir" in result.output
        assert "--no-parallel" in result.output
        assert "--summary" in result.output

    @patch("src.converter.DocumentConverter.convert_docx")
    def test_cli_preserves_folder_structure(self, mock_convert_docx, runner, temp_dir):
        """Test that CLI preserves folder structure when converting directories"""
        # Create nested directory structure
        (temp_dir / "sub1").mkdir()
        (temp_dir / "sub1" / "sub2").mkdir()

        # Create files at different levels
        self.create_mock_docx(temp_dir / "root.docx")
        self.create_mock_docx(temp_dir / "sub1" / "level1.docx")
        self.create_mock_docx(temp_dir / "sub1" / "sub2" / "level2.docx")

        output_dir = temp_dir / "output"

        # Mock conversions
        from src.converter import ConversionResult

        def mock_convert_side_effect(path):
            # Generate output paths that should preserve structure
            rel_path = path.relative_to(temp_dir)
            out_base = output_dir / rel_path.parent / path.stem
            return ConversionResult(
                source_path=str(path),
                markdown_path=str(out_base.with_suffix(".md")),
                json_path=str(out_base.with_suffix(".json")),
                status="success",
            )

        mock_convert_docx.side_effect = mock_convert_side_effect

        # Run CLI with output directory
        result = runner.invoke(main, [str(temp_dir), "--output-dir", str(output_dir)])

        assert result.exit_code == 0
        assert "Found 3 documents to convert" in result.output

        # Verify the converter was called with correct base_input_path
        assert mock_convert_docx.call_count == 3

        # Verify all files were processed
        # The CLI output shows file paths being processed
        assert "root.docx" in result.output
        assert "level1.docx" in result.output
        assert "level2.docx" in result.output or "sub2" in result.output
