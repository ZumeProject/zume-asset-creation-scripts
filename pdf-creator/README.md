# Zume PDF Book Creator

An automated tool to generate PDF books from the Zume training website using Python and Playwright.

## Features

- 🚀 **Automated PDF Generation**: Batch generate PDFs from Zume training sessions
- 🔄 **Smart Looping**: Automatically handles different session counts based on type
- 📱 **Responsive**: Configurable zoom level for optimal PDF layout (default 60%)
- 🗂️ **Organized Output**: Clean file naming and directory structure (Letter format PDFs)
- 📊 **Progress Tracking**: Real-time logging and generation summary
- 🛡️ **Error Handling**: Robust error handling with detailed logging
- 🌍 **Multi-language**: Support for any language code
- ⚙️ **Configurable**: Flexible parameters and output options

## Quick Start

### Prerequisites

- Python 3.8 or higher
- Internet connection

### Installation

1. **Clone or download this project**
   ```bash
   git clone <repository-url>
   cd zume-pdf-book-creator
   ```

2. **Run the setup script**
   ```bash
   python setup.py
   ```

   Or install manually:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

### Basic Usage

```bash
# Generate 10 sessions for Amharic (am)
python zume_pdf_generator.py --type 10 --lang am

# Generate intensive course (5 sessions) for English
python zume_pdf_generator.py --type intensive --lang en

# Generate 20 sessions for Spanish starting from session 5
python zume_pdf_generator.py --type 20 --lang es --start-session 5
```

## Command Line Options

| Option | Required | Description | Default |
|--------|----------|-------------|---------|
| `--type` | ✅ | Training type: `10`, `20`, or `intensive` | - |
| `--lang` | ✅ | Language code (e.g., `am`, `en`, `es`) | - |
| `--start-session` | ❌ | Starting session number | `1` |
| `--session` | ❌ | Generate only a specific session number (overrides `--start-session`) | - |
| `--zoom` | ❌ | Zoom level for PDF generation (e.g., 0.6, 0.8, 1.0) | `0.6` |
| `--output-dir` | ❌ | Output directory for PDFs | `output` |
| `--base-url` | ❌ | Base URL for Zume training | `https://zume.training` |
| `--timeout` | ❌ | Page load timeout in milliseconds | `60000` |
| `--max-retries` | ❌ | Maximum retry attempts for failed sessions | `2` |

## Training Types

| Type | Sessions Generated | Description |
|------|-------------------|-------------|
| `10` | 10 sessions | Standard 10-session training |
| `20` | 20 sessions | Extended 20-session training |
| `intensive` | 5 sessions | Intensive 5-session training |

## Examples

### Basic Examples

```bash
# Generate all 10 sessions in Amharic
python zume_pdf_generator.py --type 10 --lang am

# Generate intensive course in English
python zume_pdf_generator.py --type intensive --lang en

# Generate 20 sessions in Spanish
python zume_pdf_generator.py --type 20 --lang es
```

### Advanced Examples

```bash
# Start from session 3 (useful if first sessions failed)
python zume_pdf_generator.py --type 10 --lang am --start-session 3

# Generate only a specific session (useful for retrying failed sessions)
python zume_pdf_generator.py --type 10 --lang am --session 5

# Use custom zoom level for larger/smaller text
python zume_pdf_generator.py --type 10 --lang am --zoom 0.8

# Combine zoom with specific session
python zume_pdf_generator.py --type 20 --lang es --session 15 --zoom 0.7

# Save to custom directory
python zume_pdf_generator.py --type 10 --lang am --output-dir my_pdfs

# Use different base URL (for testing)
python zume_pdf_generator.py --type 10 --lang am --base-url https://staging.zume.training

# Increase timeout for slow connections (2 minutes)
python zume_pdf_generator.py --type 10 --lang am --timeout 120000

# Increase retry attempts for unreliable connections
python zume_pdf_generator.py --type 10 --lang am --max-retries 3
```

## Output

### File Naming Convention

Generated PDFs follow this pattern: `{type}_{session}_{lang}.pdf`

Examples:
- `10_1_am.pdf` - Type 10, Session 1, Amharic
- `intensive_3_en.pdf` - Intensive, Session 3, English
- `20_15_es.pdf` - Type 20, Session 15, Spanish

### Directory Structure

```
zume-pdf-book-creator/
├── output/              # Generated PDFs (default)
│   ├── am/              # Amharic PDFs
│   │   ├── 10_1_am.pdf
│   │   ├── 10_2_am.pdf
│   │   └── ...
│   ├── en/              # English PDFs
│   │   ├── intensive_1_en.pdf
│   │   └── ...
│   └── es/              # Spanish PDFs
│       └── ...
├── pdf_generation.log   # Detailed logs
└── ...
```

## Logging

The application creates detailed logs in `pdf_generation.log` and displays progress in the terminal:

```
2024-01-15 10:30:15 - INFO - Starting PDF generation for type=10, lang=am
2024-01-15 10:30:15 - INFO - Will generate 10 PDFs starting from session 1
2024-01-15 10:30:16 - INFO - Loading URL: https://zume.training/am/book/generator?type=10&session=1&lang=am
2024-01-15 10:30:18 - INFO - Generating PDF: 10_1_am.pdf
2024-01-15 10:30:20 - INFO - ✅ Successfully generated: 10_1_am.pdf
```

## Error Handling

The application includes comprehensive error handling:

- **Network Issues**: Automatic retries (2 attempts by default) and configurable timeout (60 seconds by default)
- **Invalid Parameters**: Input validation with helpful messages
- **File System Errors**: Permission and disk space checks
- **Browser Issues**: Automatic cleanup and error recovery
- **Resilient Generation**: Failed sessions are retried automatically with detailed logging

## Troubleshooting

### Common Issues

1. **"Playwright not found" error**
   ```bash
   playwright install chromium
   ```

2. **Permission denied when saving PDFs**
   ```bash
   # Check output directory permissions
   ls -la output/
   
   # Or use a different output directory
   python zume_pdf_generator.py --type 10 --lang am --output-dir ~/Documents/pdfs
   ```

3. **Network timeout errors**
   - Check internet connection
   - Try again later (website might be temporarily unavailable)
   - Verify the website URL is accessible in your browser
   - Increase timeout: `--timeout 120000` (2 minutes)
   - Enable more retries: `--max-retries 3`

4. **Memory issues with large batches**
   - Generate smaller batches using `--start-session`
   - Generate individual sessions using `--session N`
   - Close other applications to free memory

5. **PDF layout issues**
   - Adjust zoom level with `--zoom` parameter (try 0.5-1.0 range)
   - Smaller zoom (e.g., 0.5) fits more content per page
   - Larger zoom (e.g., 0.8) makes text more readable

### Getting Help

- Check the log file `pdf_generation.log` for detailed error information
- Ensure you have a stable internet connection
- Verify the Zume training website is accessible
- Make sure Python 3.8+ is installed

## Development

### Project Structure

```
zume-pdf-book-creator/
├── zume_pdf_generator.py    # Main application
├── setup.py                 # Setup script
├── requirements.txt         # Dependencies
├── README.md               # Documentation
└── output/                 # Generated PDFs
```

### Running Tests

```bash
# Install development dependencies
pip install pytest pytest-asyncio

# Run tests (when available)
pytest
```

### Code Formatting

```bash
# Install formatting tools
pip install black flake8

# Format code
black zume_pdf_generator.py

# Check code quality
flake8 zume_pdf_generator.py
```

## License

This project is created for Zume Training. Please respect the Zume training content and use this tool responsibly.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

**Need help?** Check the troubleshooting section above or review the log files for detailed error information. 