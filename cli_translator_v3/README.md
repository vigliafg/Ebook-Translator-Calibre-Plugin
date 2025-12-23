# Ebook Translator CLI v3 (Monolithic)

This is a **monolithic standalone version** of the Ebook Translator. All internal modules have been consolidated into a single file `cli_translator_v3.py` for maximum portability and ease of use as a script.

## Features
- **Monolithic**: Single-file script (excluding external libraries).
- **High Performance**: Multithreaded OpenRouter engine with JSON batching.
- **Literary Quality**: Experts Italian translation prompt included.
- **Resilient**: Automatic fallback to sequential translation if AI batching fails.

## Installation

1. Install the required libraries:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Set your API key:
```powershell
# Windows
$env:OPENROUTER_API_KEY = "your_key"
```

Run the script directly:
```bash
python cli_translator_v3.py path/to/book.epub -OPR --model openai/gpt-oss-120b --threads 8
```

## Flags
- `-OPR`: Use OpenRouter (AI).
- `--model`: Model ID (e.g., `deepseek/deepseek-chat`).
- `--threads`: Number of parallel threads (default: 8).
