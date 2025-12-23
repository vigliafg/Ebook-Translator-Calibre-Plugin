# Ebook Translator CLI

This is a **monolithic standalone version** of the Ebook Translator. It is designed for maximum portability and ease of use as a command-line tool, supporting both Google Translate (Free) and various AI models via OpenRouter.

## Features

- **Monolithic Architecture**: All logic is contained in a single script `cli_translator.py`.
- **Dual Translation Engines**:
  - **Google Translate (Free)**: Quick, no-cost translation using Google's translation API.
  - **AI Models (OpenRouter)**: High-quality literary translation using models like GPT-4, DeepSeek, or specialized open-source models (e.g., `openai/gpt-oss-120b`).
- **Smart Batching**: Content is processed in optimized batches using JSON to preserve structure and improve performance.
- **TOC Translation**: Fully recursive translation of the Table of Contents.
- **Multithreaded**: Parallel processing for fast execution when using AI engines.
- **Robust Sanitization**: Automatically cleans AI-generated debris like "Translation:" labels or extraneous quotes.

## Installation

1. Clone or download this repository.
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### 1. Google Translate (Default)
Simple and free translation. No API key required.
```bash
python cli_translator.py path/to/book.epub
```

### 2. AI Models (OpenRouter)
For significantly higher literary quality and context awareness.

#### Set your API Key:
```powershell
# Windows (PowerShell)
$env:OPENROUTER_API_KEY = "your_api_key_here"
```

#### Run with OpenRouter:
```bash
# Basic usage with default model (openai/gpt-oss-120b)
python cli_translator.py path/to/book.epub -OPR

# Specify a custom model and thread count
python cli_translator.py path/to/book.epub -OPR --model deepseek/deepseek-chat --threads 12
```

## Command Line Flags

| Flag | Description | Default |
| :--- | :--- | :--- |
| `input` | Path to the source EPUB file. | (Required) |
| `-OPR` | Use OpenRouter engine instead of Google Translate. | Off |
| `--model` | Specific OpenRouter model ID. | `openai/gpt-oss-120b` |
| `--threads` | Number of parallel translation threads. | `8` |

## Requirements

- Python 3.x
- `ebooklib`: For EPUB reading and writing.
- `lxml`: For high-performance XML/HTML parsing.
- `mechanize`: Browser-like interactions for translation requests.
- `cssselect`: For advanced element selection.
- `PySocks`: (Optional) For proxy support.

## Output
The script generates a new EPUB file named `[original_name]_ITALIANO.epub` in the same directory as the input file.
