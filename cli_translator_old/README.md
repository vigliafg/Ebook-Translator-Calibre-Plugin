# Ebook Translator CLI

This is a standalone command-line tool for converting English EPUB ebooks to Italian using Google Translate (Free).
It preserves the original formatting, images, and structure of the EPUB.

## Features

- **Standalone**: No dependence on Calibre.
- **Translation Engine**: Uses Google Translate (Free edition).
- **Smart Formatting**: Maintains the layout, style, and images of the original ebook.
- **Monolingual Output**: Generates a fully translated Italian EPUB (replacing the English text).
- **TOC Translation**: Automatically translates the Table of Contents.

## Requirements

- Python 3.x

## Installation

1. Navigate to this directory (or the project root).
2. Install the required Python packages:

   ```bash
   pip install -r requirements.txt
   ```

## Usage

You can run the translator directly using Python.

**Running from the parent directory:**

```bash
python -m cli_translator.console path/to/your/book.epub
```

**Output:**

The tool will generate a new file ending in `_ITALIANO.epub` in the same directory as the input file.

Example:
`book.epub` -> `book_ITALIANO.epub`

## Project Structure

- `console.py`: Main entry point and orchestration logic.
- `utils.py`: Utility functions (logging, networking).
- `element.py`: Core logic for HTML element extraction and manipulation.
- `engines/`: Translation engine implementations (Google, etc.).
- `config.py`: Configuration settings.

## Notes

- The translation speed is intentionally rate-limited to respectful usage of the free Google Translate endpoint.
- If you encounter `KeyboardInterrupt` or errors, the partial output might not be valid.
