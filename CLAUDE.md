# CLAUDE.md - Development Notes for AI Assistants

This document contains important context and improvement suggestions for AI assistants working on this codebase.

## Project Overview

This is a document conversion tool that transforms PDF, DOCX, and PPTX files into Markdown and JSON formats. The tool uses:
- `marker-pdf[full]` for advanced PDF text extraction
- `python-docx` for Word documents
- `python-pptx` for PowerPoint presentations
- `uv` as the package manager (NOT pip)

## Key Technical Details

### Package Management
- **ALWAYS use `uv` commands**: `uv add`, `uv sync`, `uv run`
- **NEVER use pip commands**
- The project requires Python >=3.10 due to marker-pdf requirements

### Marker-PDF Integration
The correct imports for marker-pdf are:
```python
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered
```

### Folder Structure Preservation
- When converting directories with `--output-dir`, the original folder structure is preserved
- The `base_input_path` parameter in `DocumentConverter` tracks the root directory
- Single files are placed flat in the output directory without path preservation

## Future Improvements

### 1. Enhanced Format Support
- **Add support for RTF files**: Use `python-rtf` or `striprtf` library
- **Add support for ODT files**: Use `odfpy` library
- **Add support for EPUB files**: Use `ebooklib` library
- **Add support for HTML files**: Use `beautifulsoup4` with custom markdown conversion

### 2. Performance Optimizations
- **Implement caching**: Cache converted files to avoid re-processing unchanged documents
- **Add GPU detection**: Automatically detect and utilize CUDA when available for marker-pdf
- **Optimize memory usage**: Stream large files instead of loading entirely into memory
- **Add batch size configuration**: Allow users to configure parallel processing batch size

### 3. Output Enhancements
- **Add image extraction**: Save embedded images from documents to separate files
- **Implement table preservation**: Better table formatting in markdown output
- **Add syntax highlighting**: Detect and preserve code blocks with appropriate language tags
- **Create HTML output option**: Generate styled HTML in addition to markdown
- **Add combined output mode**: Option to merge all conversions into a single file

### 4. CLI Improvements
- **Add watch mode**: Monitor directories for new files and auto-convert
- **Implement dry-run option**: Show what would be converted without actual processing
- **Add filter options**: Filter by file size, date, or pattern
- **Progress persistence**: Save progress for resuming interrupted batch conversions
- **Add configuration file support**: Allow `.docs2mdrc` or similar for default options

### 5. Quality Improvements
- **Add OCR for scanned PDFs**: Integrate with Suriya for PDFs without text layers
- **Implement language detection**: Auto-detect document language for better processing
- **Add validation**: Verify output quality and completeness
- **Implement retry logic**: Automatic retry for failed conversions with backoff

### 6. Integration Features
- **Add API mode**: REST API endpoint for document conversion service
- **Implement plugins**: Allow custom converters for proprietary formats
- **Add cloud storage support**: Direct conversion from/to S3, Google Drive, etc.
- **Create GitHub Action**: Automated conversion for repository documentation

### 7. Testing Improvements
- **Add integration tests with real files**: Test with actual PDF, DOCX, PPTX samples
- **Implement performance benchmarks**: Track conversion speed over time
- **Add visual regression tests**: For formats that include layout preservation
- **Create test data generator**: Generate test documents programmatically

### 8. Documentation Enhancements
- **Add conversion examples**: Show before/after for each format
- **Create video tutorial**: Demonstrate installation and usage
- **Add troubleshooting guide**: Expand with common issues and solutions
- **Implement inline help**: More detailed help messages in CLI

## Code Quality Guidelines

When making improvements:
1. **Maintain backward compatibility**: Don't break existing CLI arguments
2. **Follow existing patterns**: Use the same style for new converters
3. **Add comprehensive tests**: Every new feature needs unit tests
4. **Update documentation**: Keep README.md and help text in sync
5. **Use type hints**: All new functions should have proper type annotations
6. **Handle errors gracefully**: Never let the tool crash on bad input

## Common Pitfalls to Avoid

1. **Don't use synchronous I/O in parallel processing**: Will cause deadlocks
2. **Be careful with memory**: Large PDFs can consume significant RAM
3. **Test with various encodings**: Documents may have different character encodings
4. **Consider path separators**: Tool should work on Windows, Mac, and Linux
5. **Respect user's file system**: Never modify original files

## Testing Commands

Always run these before committing:
```bash
# Format code
uv run ruff format src tests

# Check linting
uv run ruff check src tests

# Run tests
uv run pytest

# Check test coverage
uv run pytest --cov=src --cov-report=html
```

Note: Tests currently show Pydantic deprecation warnings from marker-pdf dependencies. These are expected and don't affect functionality.

## Debugging Tips

1. **For marker-pdf issues**: Check if models are downloading correctly
2. **For memory issues**: Use `--no-parallel` flag
3. **For import errors**: Ensure `uv sync` has been run
4. **For permission errors**: Check file and directory permissions

## Environment Variables

Consider adding support for:
- `DOCS2MD_OUTPUT_DIR`: Default output directory
- `DOCS2MD_PARALLEL_WORKERS`: Number of parallel workers
- `DOCS2MD_LOG_LEVEL`: Logging verbosity
- `DOCS2MD_CACHE_DIR`: Cache directory for converted files