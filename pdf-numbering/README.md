# PDF Page Numbering Tool

This script adds page numbers to PDF files, placing the numbers at the bottom center of each page (except the first page).

## Requirements

- Python 3.6 or higher
- PyPDF2 and reportlab libraries

## Installation

1. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

1. Place PDF files that need page numbers in the `unnumbered` folder.
2. Run the script:
   ```
   python add_numbers.py
   ```
3. Numbered PDFs will be saved in the `numbered` folder, and the original files will be deleted.

## Features

- Automatically processes all PDFs in the `unnumbered` folder
- Adds page numbers centered at the bottom of each page
- Skips adding a page number to the first page (cover page)
- Saves processed PDFs to the `numbered` folder
- Removes original files after successful processing 