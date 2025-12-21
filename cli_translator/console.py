import sys
import os
import argparse
import time
import logging
import traceback

try:
    import ebooklib
    from ebooklib import epub
    from lxml import etree
except ImportError:
    print("Please install dependencies: pip install -r requirements.txt")
    sys.exit(1)

from .config import get_config
from .element import get_element_handler, get_page_elements
from .engines.google import GoogleFreeTranslate, GoogleFreeTranslateNew

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger('cli')

class PageWrapper:
    def __init__(self, item, data):
        self.item = item
        self.id = item.file_name
        self.href = item.file_name
        self.data = data

class Paragraph:
    def __init__(self, original, translation):
        self.original = original
        self.translation = translation

def process_epub(input_path):
    if not os.path.exists(input_path):
        log.error(f"Input file not found: {input_path}")
        return

    output_path = input_path.rsplit('.', 1)[0] + '_ITALIANO.epub'
    log.info(f"Processing {input_path} -> {output_path}")

    try:
        book = epub.read_epub(input_path)
    except Exception as e:
        log.error(f"Failed to read epub: {e}")
        return

    # Initialize Engine
    # GoogleFreeTranslateNew seems better/newer, fallback to Old if issues?
    # User asked for "Google Translate Free".
    engine = GoogleFreeTranslateNew() 
    # Engine expects keys from languages.py (Full Names), not codes
    engine.set_source_lang('English')
    engine.set_target_lang('Italian')

    # Iterate items
    items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
    wrapped_pages = []
    
    log.info("Parsing book content...")
    for item in items:
        try:
            content = item.get_content()
            # Ebooklib returns bytes
            # Use recover=True for loose XML/XHTML parsing
            tree = etree.fromstring(content, parser=etree.XMLParser(recover=True, resolve_entities=False))
            wrapped_pages.append(PageWrapper(item, tree))
        except Exception as e:
            log.warning(f"Failed to parse {item.file_name}, skipping: {e}")

    if not wrapped_pages:
        log.error("No parseable content found.")
        return

    # Extract elements
    # get_page_elements sorts pages by href internally
    log.info("Extracting text segments...")
    elements = get_page_elements(wrapped_pages)

    # Prepare Handler
    placeholder = ('{{{{id_{}}}}}', r'({{\s*)+id\s*_\s*{}\s*(\s*}})+')
    separator = '\n\n'
    # Use 'only' to replace original text with translation
    handler = get_element_handler(placeholder, separator, 'only')

    # Prepare originals
    originals = handler.prepare_original(elements)
    
    paragraphs = []
    total = len(originals)
    log.info(f"Found {total} segments to translate.")

    count = 0
    start_time = time.time()

    for item in originals:
        # item: (oid, md5, raw, content, ignored, attrs, page_id)
        content = item[3]
        ignored = item[4]

        trans_text = None
        if not ignored and content.strip():
            try:
                # Basic rate limiting
                trans_text = engine.translate(content)
                # Small sleep to be nice to the free endpoint
                time.sleep(0.3) 
            except Exception as e:
                log.error(f"Error translating segment {item[0]}: {e}")
                # Optional: keep original or mark failure
                trans_text = "[Translation Failed]"
        
        if trans_text:
            paragraphs.append(Paragraph(content, trans_text))
        
        count += 1
        if count % 10 == 0:
            elapsed = time.time() - start_time
            rate = count / elapsed if elapsed > 0 else 0
            log.info(f"Progress: {count}/{total} segments ({rate:.1f} seg/s)")

    # Recompose
    log.info("Recomposing epub...")
    handler.add_translations(paragraphs)



    # Update Items in Book
    for page in wrapped_pages:
        # Serialize tree back to bytes
        new_content = etree.tostring(page.data, encoding='utf-8', method='xml')
        if not new_content:
             log.warning(f"Warning: Serialized content is empty for {page.id}")
        page.item.set_content(new_content)

    # Sanitize TOC UIDs to prevent ebooklib write error
    def fix_uid(toc_tree):
        for item in toc_tree:
            if isinstance(item, (list, tuple)):
                fix_uid(item)
            elif hasattr(item, 'uid') and not item.uid:
                # Assign a generic UID if missing
                item.uid = f'toc-{id(item)}'

    fix_uid(book.toc)

    # Translate Table of Contents
    log.info("Translating Table of Contents...")
    def translate_toc(toc_tree):
        for item in toc_tree:
            if isinstance(item, (list, tuple)):
                translate_toc(item)
            elif hasattr(item, 'title') and item.title:
                try:
                    # Translate title
                    trans_title = engine.translate(item.title)
                    if trans_title:
                         item.title = trans_title
                    time.sleep(0.3)
                except Exception as e:
                    log.warning(f"Failed to translate TOC item '{item.title}': {e}")
    
    translate_toc(book.toc)

    # Write output
    try:
        epub.write_epub(output_path, book)
        log.info(f"Success! Translated epub saved to: {output_path}")
    except Exception:
        log.error(f"Failed to write output epub: {traceback.format_exc()}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Translate English Epub to Italian using Google Free Translate")
    parser.add_argument('input_epub', help="Path to input epub file")
    args = parser.parse_args()
    process_epub(args.input_epub)
