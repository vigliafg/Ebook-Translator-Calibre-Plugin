# Ebook Translator CLI v2 (High Performance)

This is a standalone, high-performance command-line tool for converting English EPUB ebooks to Italian. It has been highly optimized for **literary translation quality** and **massive throughput** (up to 5 segments/second).

## Key Features

-   **Parallel Processing**: Multithreaded translation architecture (up to 8 parallel threads).
-   **Massive Batching**: Processes 20 segments per request for maximum cost-efficiency and speed.
-   **Advanced AI Engines**: Deeply integrated with **OpenRouter**, supporting low-cost, high-quality models.
-   **Robust JSON Mapping**: Uses a specialized ID-indexed JSON format to ensure **zero translation omissions** and perfect alignment, even with unpredictable LLM behavior.
-   **Literary Translation Prompt**: Pre-configured with an expert Italian literary translator prompt to preserve style, tone, and flow.
-   **Standalone**: No need for Calibre; works directly on `.epub` files.

---

## Installation & Setup

1.  **Posizione**: Assicurati di essere nella cartella principale del progetto (`Ebook-Translator-Calibre-Plugin`).
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

---

## Configuration

Before using OpenRouter, set your API key as an environment variable:

```powershell
# Windows (PowerShell)
$env:OPENROUTER_API_KEY = "your_key_here"

# Linux / Mac
export OPENROUTER_API_KEY="your_key_here"
```

---

## Usage Examples

### 1. High-Speed Production Run (DeepSeek V3)
Our primary recommendation for cost, speed, and quality.
```bash
python -m cli_translator_v2.console path/to/your/book.epub -OPR --model deepseek/deepseek-chat --threads 8
```

### 2. Maximum Speed / Ultra-Low Cost (Gemini 1.5 Flash)
Best for very large books or quick drafts.
```bash
python -m cli_translator_v2.console path/to/your/book.epub -OPR --model google/gemini-flash-1.5 --threads 8
```

### 3. High-Quality Literary Fallback (Llama 3.1 70B)
Excellent for poetic or complex prose.
```bash
python -m cli_translator_v2.console path/to/your/book.epub -OPR --model meta-llama/llama-3.1-70b-instruct --threads 4
```

### 4. Simple Google Translate (Free/Sequential)
No API key required, but slow and limited.
```bash
python -m cli_translator_v2.console path/to/your/book.epub
```

---

## Command Flags

-   `-OPR`: Activates the OpenRouter engine.
-   `--model [MODEL_ID]`: Specify any model available on OpenRouter (default: `deepseek/deepseek-chat`).
-   `--threads [N]`: Set the number of parallel threads (default: 8). Use 8 for maximum speed.
-   `--batch [N]`: (Internal) The system uses a fixed optimized batch size of 20 for JSON stability.

---

## Performance Notes & Suggestions

> [!TIP]
> **Recommended Settings**: For the best balance of speed and stability, use `--model deepseek/deepseek-chat --threads 8`. This typically yields ~4-5 segments per second.

-   **API Limits**: If you encounter `429 (Too Many Requests)`, reduce the number of threads (e.g., `--threads 4`).
-   **JSON Stability**: The ID-indexed mapping (`{"0": "...", "1": "..."}`) is designed to catch cases where the model forgets a segment. If a segment is missed, the tool will fallback to sequential translation for that specific batch automatically.
-   **Output**: The translated file is saved as `[ORIGINAL]_ITALIANO.epub`.

## Supporto Letterario (Note Traduttore)
Il prompt di sistema è stato tarato per produrre un italiano **elegante e colto**, preservando:
-   Dialoghi e registri linguistici.
-   La distinzione tra "Lei", "Voi" e "Tu" se presente nel contesto (sebbene l'AI tenda al "Lei" o "Tu" moderno, lo stile cercato è classico).
-   Mantenimento invariato di nomi propri e termini tecnici riservati (tramite placeholder lxml).
