# Document to Markdown Converter

This Python tool recursively scans directories for PDF, DOCX, and PPTX files and converts them to Markdown (.md) and JSON (.json) formats with metadata extraction.

## Features

- **Multi-format Support**: Converts PDF, DOCX, and PPTX files
- **Recursive Scanning**: Automatically finds all supported documents in subdirectories
- **Dual Output**: Generates both Markdown and JSON formats for each document
- **Advanced PDF Processing**: Uses marker-pdf for high-quality PDF text extraction
- **Metadata Extraction**: Captures document metadata (author, creation date, etc.)
- **Parallel Processing**: Converts multiple files concurrently for faster processing
- **Rich CLI Interface**: Progress bars and colored output using Rich
- **Flexible Output**: Option to specify custom output directory structure

## Installation

This project uses `uv` as the package manager. If you don't have `uv` installed:

```bash
# Install uv (macOS/Linux)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install uv (Windows)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Clone the repository and install dependencies:

```bash
git clone https://github.com/yourusername/docs_to_markdown.git
cd docs_to_markdown

# Install the package and dependencies
uv sync
uv add 'marker-pdf[full]' rich click torch
```

## Usage

### Basic Usage

Convert a single file:

```bash
docs2md /path/to/document.pdf
```

Convert all documents in a directory recursively:

```bash
docs2md /path/to/documents/
```

### Command Line Options

```bash
docs2md [OPTIONS] PATH

Options:
  -o, --output-dir PATH  Output directory (default: same as source)
  --no-parallel          Disable parallel processing
  -s, --summary          Show conversion summary table
  --help                 Show this message and exit
```

### Examples

1. **Convert a single PDF with summary**:
   ```bash
   docs2md ~/Documents/report.pdf --summary
   ```

2. **Convert all documents in a folder to a specific output directory**:
   ```bash
   docs2md ~/Documents --output-dir ~/Converted/Markdown
   ```

3. **Convert documents sequentially (useful for debugging)**:
   ```bash
   docs2md ~/Documents --no-parallel
   ```

## Output Format

### Markdown Files (.md)

- **PDF**: High-quality text extraction with layout preservation
- **DOCX**: Preserves headings, paragraphs, and basic formatting (bold, italic)
- **PPTX**: Organized by slides with titles and speaker notes

### JSON Files (.json)

Each JSON file contains:
- `source`: Original file path
- `type`: Document type (pdf, docx, pptx)
- `content`: Full extracted text
- `metadata`: Document-specific metadata
  - PDF: Page count, detected language
  - DOCX: Author, title, creation/modification dates
  - PPTX: Slide count, author, title, dates

## Architecture

The converter is built with a modular architecture:

- `DocumentConverter`: Main class orchestrating conversions
- `convert_pdf()`: Uses marker-pdf for advanced PDF processing
- `convert_docx()`: Uses python-docx for Word documents
- `convert_pptx()`: Uses python-pptx for PowerPoint files

## Development

### Running Tests

```bash
# Install development dependencies
uv sync --dev

# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_converter.py
```

### Code Quality

```bash
# Run linter
ruff check src tests

# Format code
ruff format src tests
```

### Project Structure

```
docs_to_markdown/
├── src/
│   ├── __init__.py
│   └── converter.py       # Main converter implementation
├── tests/
│   ├── __init__.py
│   ├── test_converter.py  # Unit tests
│   └── test_integration.py # Integration tests
├── pyproject.toml         # Project configuration
├── README.md             # This file
└── CLAUDE.md            # Development notes for AI assistants
```

## Dependencies

- **click**: Command-line interface
- **rich**: Beautiful terminal output
- **torch**: Required by marker-pdf
- **marker-pdf[full]**: Advanced PDF text extraction
- **python-docx**: DOCX file processing
- **python-pptx**: PPTX file processing

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError for marker**:
   - Ensure you've installed with `uv add 'marker-pdf[full]'`
   - Python version must be >=3.10

2. **CUDA/GPU errors**:
   - The tool works with CPU if CUDA is not available
   - For GPU acceleration, ensure PyTorch CUDA is properly installed

3. **Memory issues with large PDFs**:
   - Use `--no-parallel` to process files sequentially
   - Consider processing large files individually

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [marker-pdf](https://github.com/datalab-to/marker) for excellent PDF processing
- [Rich](https://github.com/Textualize/rich) for beautiful CLI output
- [Click](https://click.palletsprojects.com/) for robust command-line parsing