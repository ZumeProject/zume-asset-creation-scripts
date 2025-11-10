# Zume PDF Book Creator

An automated tool to generate PDF books from the Zume training website using Python and Playwright. This project includes two scripts: a single-run generator and a batch generator for processing multiple type/language combinations.

## Features

- 🚀 **Automated PDF Generation**: Generate PDFs from Zume training sessions automatically
- 📦 **Batch Processing**: Process multiple type/language combinations in one run
- 🔄 **Smart Looping**: Automatically handles different session counts based on type
- 📱 **Responsive**: Configurable zoom level for optimal PDF layout (default 0.8)
- 🗂️ **Organized Output**: Clean file naming and directory structure (Letter format PDFs)
- 📊 **Progress Tracking**: Real-time logging and generation summary
- 🛡️ **Error Handling**: Robust error handling with automatic retries and detailed logging
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
   cd pdf-creator
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

## Scripts Overview

This project includes two main scripts:

1. **`zume_pdf_generator.py`** - Generates PDFs for a single type/language combination
2. **`batch_pdf_generator.py`** - Batch generates PDFs for multiple type/language combinations

## Usage

### Single Generation (`zume_pdf_generator.py`)

Use this script when you need to generate PDFs for a single type and language combination.

#### Basic Usage

```bash
# Generate 10 sessions for Amharic (am)
python zume_pdf_generator.py --type 10 --lang am

# Generate intensive course (5 sessions) for English
python zume_pdf_generator.py --type intensive --lang en

# Generate 20 sessions for Spanish
python zume_pdf_generator.py --type 20 --lang es
```

#### Command Line Options

| Option | Required | Description | Default |
|--------|----------|-------------|---------|
| `--type` | ✅ | Training type: `10`, `20`, or `intensive` | - |
| `--lang` | ✅ | Language code (e.g., `am`, `en`, `es`) | - |
| `--start-session` | ❌ | Starting session number | `1` |
| `--session` | ❌ | Generate only a specific session number (overrides `--start-session`) | - |
| `--zoom` | ❌ | Zoom level for PDF generation (e.g., 0.6, 0.8, 1.0) | `0.8` |
| `--output-dir` | ❌ | Output directory for PDFs | `output` |
| `--base-url` | ❌ | Base URL for Zume training | `https://zume.training` |
| `--timeout` | ❌ | Page load timeout in milliseconds | `60000` |
| `--max-retries` | ❌ | Maximum retry attempts for failed sessions | `2` |

#### Single Generation Examples

```bash
# Generate all 10 sessions in Amharic
python zume_pdf_generator.py --type 10 --lang am

# Generate intensive course in English
python zume_pdf_generator.py --type intensive --lang en

# Generate 20 sessions in Spanish starting from session 5
python zume_pdf_generator.py --type 20 --lang es --start-session 5

# Generate only a specific session (useful for retrying failed sessions)
python zume_pdf_generator.py --type 10 --lang am --session 5

# Use custom zoom level for larger/smaller text
python zume_pdf_generator.py --type 10 --lang am --zoom 0.9

# Save to custom directory
python zume_pdf_generator.py --type 10 --lang am --output-dir my_pdfs

# Increase timeout for slow connections (2 minutes)
python zume_pdf_generator.py --type 10 --lang am --timeout 120000

# Increase retry attempts for unreliable connections
python zume_pdf_generator.py --type 10 --lang am --max-retries 3
```

### Batch Generation (`batch_pdf_generator.py`)

Use this script to generate PDFs for multiple type/language combinations in one run. The batch generator automatically loops through all combinations and generates PDFs for each.

#### Basic Usage

```bash
# Generate PDFs for multiple types and languages
python batch_pdf_generator.py --types 10 20 --languages en es

# Generate intensive course for multiple languages
python batch_pdf_generator.py --types intensive --languages am en es

# Generate for single type but multiple languages
python batch_pdf_generator.py --types 10 --languages en es fr de
```

#### Command Line Options

| Option | Required | Description | Default |
|--------|----------|-------------|---------|
| `--types` | ✅ | Training types: `10`, `20`, `intensive` (can specify multiple) | - |
| `--languages` | ✅ | Language codes (e.g., `am`, `en`, `es`) - can specify multiple | - |
| `--start-session` | ❌ | Starting session number for all generations | `1` |
| `--session` | ❌ | Generate only a specific session number for all combinations (overrides `--start-session`) | - |
| `--zoom` | ❌ | Zoom level for PDF generation | `0.8` |
| `--output-dir` | ❌ | Output directory for PDFs | `output` |
| `--base-url` | ❌ | Base URL for Zume training | `https://zume.training` |
| `--timeout` | ❌ | Page load timeout in milliseconds | `60000` |
| `--max-retries` | ❌ | Maximum retry attempts for failed sessions | `2` |

#### Batch Generation Examples

```bash
# Generate PDFs for types 10 and 20 in English and Spanish (4 total combinations)
python batch_pdf_generator.py --types 10 20 --languages en es

# Generate intensive course for multiple languages
python batch_pdf_generator.py --types intensive --languages am en es

# Generate all types for all languages
python batch_pdf_generator.py --types 10 20 intensive --languages am en es fr de

# Generate specific session for multiple combinations
python batch_pdf_generator.py --types 10 20 --languages en es --session 5

# Custom output directory
python batch_pdf_generator.py --types 10 --languages en es --output-dir my_pdfs

# Custom zoom level for all batch generations
python batch_pdf_generator.py --types 10 20 --languages en es --zoom 0.9

# Increased timeout for all generations
python batch_pdf_generator.py --types 10 20 --languages en es --timeout 120000
```

## Training Types

| Type | Sessions Generated | Description |
|------|-------------------|-------------|
| `10` | 10 sessions | Standard 10-session training |
| `20` | 20 sessions | Extended 20-session training |
| `intensive` | 5 sessions | Intensive 5-session training |

## Output

### File Naming Convention

Generated PDFs follow this pattern: `{type}_{session}_{lang}.pdf`

Examples:
- `10_1_am.pdf` - Type 10, Session 1, Amharic
- `intensive_3_en.pdf` - Intensive, Session 3, English
- `20_15_es.pdf` - Type 20, Session 15, Spanish

### Directory Structure

```
pdf-creator/
├── output/              # Generated PDFs (default)
│   ├── am/              # Amharic PDFs
│   │   ├── 10_1_am.pdf
│   │   ├── 10_2_am.pdf
│   │   ├── 20_1_am.pdf
│   │   └── ...
│   ├── en/              # English PDFs
│   │   ├── 10_1_en.pdf
│   │   ├── intensive_1_en.pdf
│   │   └── ...
│   └── es/              # Spanish PDFs
│       └── ...
├── pdf_generation.log          # Detailed logs (single generation)
├── batch_pdf_generation.log    # Detailed logs (batch generation)
└── ...
```

## Logging

Both scripts create detailed logs and display progress in the terminal:

### Single Generation Logs (`pdf_generation.log`)

```
2024-01-15 10:30:15 - INFO - Starting PDF generation for type=10, lang=am
2024-01-15 10:30:15 - INFO - Will generate 10 PDFs starting from session 1
2024-01-15 10:30:16 - INFO - Loading URL: https://zume.training/am/book/generator?type=10&session=1&lang=am
2024-01-15 10:30:18 - INFO - Generating PDF: 10_1_am.pdf
2024-01-15 10:30:20 - INFO - ✅ Successfully generated: 10_1_am.pdf
```

### Batch Generation Logs (`batch_pdf_generation.log`)

```
2024-01-15 10:30:15 - INFO - 🚀 Starting batch PDF generation
2024-01-15 10:30:15 - INFO - Types: ['10', '20']
2024-01-15 10:30:15 - INFO - Languages: ['en', 'es']
2024-01-15 10:30:15 - INFO - Total combinations: 4
2024-01-15 10:30:15 - INFO - 📊 Progress: 1/4
2024-01-15 10:30:15 - INFO - 🔄 Running generation for type=10, lang=en
...
2024-01-15 10:35:00 - INFO - ✅ Successfully completed generation for type=10, lang=en
```

Both scripts provide summary reports at the end showing successful and failed generations.

## Error Handling

Both applications include comprehensive error handling:

- **Network Issues**: Automatic retries (2 attempts by default) and configurable timeout (60 seconds by default)
- **Invalid Parameters**: Input validation with helpful messages
- **File System Errors**: Permission and disk space checks
- **Browser Issues**: Automatic cleanup and error recovery
- **Resilient Generation**: Failed sessions are retried automatically with detailed logging
- **Batch Tracking**: Batch generator tracks success/failure for each combination and provides a summary

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
   - Process types/languages separately instead of all at once
   - Close other applications to free memory

5. **PDF layout issues**
   - Adjust zoom level with `--zoom` parameter (try 0.5-1.0 range)
   - Smaller zoom (e.g., 0.5) fits more content per page
   - Larger zoom (e.g., 0.8-1.0) makes text more readable

6. **Batch generation partially fails**
   - Check `batch_pdf_generation.log` for specific failure details
   - Re-run only failed combinations using `zume_pdf_generator.py`
   - Use `--session N` to retry specific failed sessions

### Getting Help

- Check the log files (`pdf_generation.log` or `batch_pdf_generation.log`) for detailed error information
- Ensure you have a stable internet connection
- Verify the Zume training website is accessible
- Make sure Python 3.8+ is installed
- Review the command-line help: `python zume_pdf_generator.py --help` or `python batch_pdf_generator.py --help`

## Development

### Project Structure

```
pdf-creator/
├── zume_pdf_generator.py      # Single generation script
├── batch_pdf_generator.py     # Batch generation script
├── setup.py                   # Setup script
├── requirements.txt           # Dependencies
├── README.md                  # Documentation
├── assets/
│   └── cover-page.pdf         # Cover page asset
└── output/                    # Generated PDFs
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
black *.py

# Check code quality
flake8 *.py
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
