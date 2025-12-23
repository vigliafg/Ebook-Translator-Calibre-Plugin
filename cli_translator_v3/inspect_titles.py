import ebooklib
from ebooklib import epub

def print_toc(toc, level=0):
    for item in toc:
        if isinstance(item, (list, tuple)):
            print_toc(item, level + 1)
        else:
            title = getattr(item, 'title', 'No Title')
            print(f"{'  ' * level} - RAW: {repr(title)}")

book = epub.read_epub(r'c:\Users\vigli\Documents\GitHub\Ebook-Translator-Calibre-Plugin\cli_translator_v3\glory.epub')
print("TOC Titles (Original):")
print_toc(book.toc)
