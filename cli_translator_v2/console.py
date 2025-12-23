import os
import re
import sys
import time
import json
import logging
import argparse
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
from .engines.openrouter import OpenRouter
from concurrent.futures import ThreadPoolExecutor, as_completed

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

def process_epub(input_path, use_openrouter=False, model=None, threads=4):
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
    if use_openrouter:
        log.info(f"Using OpenRouter Engine (Model: {model or 'Default'})")
        engine = OpenRouter(model=model)
        engine.set_source_lang('English')
        engine.set_target_lang('Italian')
    else:
        # Default Google
        engine = GoogleFreeTranslateNew() 
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
    
    # Filter non-ignored and non-empty
    valid_items = []
    for item in originals:
        content = item[3]
        ignored = item[4]
        if not ignored and content.strip():
            valid_items.append(item)

    # Batching logic
    BATCH_SIZE = 20 # Safer size for JSON stability across all models
    
    if hasattr(engine, 'translate_batch') and use_openrouter:
        log.info(f"Parallel Batch processing enabled (Size: {BATCH_SIZE}, Threads: {threads})...")
        
        # Prepare batches
        batches = [valid_items[i:i + BATCH_SIZE] for i in range(0, len(valid_items), BATCH_SIZE)]
        
        def translate_chunk(batch_info):
            batch_idx, batch = batch_info
            batch_contents = [item[3] for item in batch]
            translated_batch = engine.translate_batch(batch_contents)
            
            if translated_batch:
                return batch_idx, [(batch[idx][3], t_text) for idx, t_text in enumerate(translated_batch) if idx < len(batch)]
            else:
                log.warning(f"Batch {batch_idx} failed, falling back to sequential.")
                results = []
                for item in batch:
                    try:
                        t_text = engine.translate(item[3])
                        results.append((item[3], t_text))
                        time.sleep(1) # Minimal sleep to avoid 429 during fallback
                    except Exception as e:
                        log.error(f"Translation failed: {e}")
                return batch_idx, results

        all_batch_results = {}
        with ThreadPoolExecutor(max_workers=threads) as executor:
            future_to_batch = {executor.submit(translate_chunk, (i, b)): i for i, b in enumerate(batches)}
            
            for future in as_completed(future_to_batch):
                batch_idx, batch_res = future.result()
                all_batch_results[batch_idx] = batch_res
                
                count += len(batch_res)
                elapsed = time.time() - start_time
                rate = count / elapsed if elapsed > 0 else 0
                log.info(f"Progress: {min(count, len(valid_items))}/{len(valid_items)} segments ({rate:.1f} seg/s)")
        
        # Assemble in original order
        for i in range(len(batches)):
            if i in all_batch_results:
                for orig, trans in all_batch_results[i]:
                    paragraphs.append(Paragraph(orig, trans))

    else:
        # Sequential
        for item in originals:
            content = item[3]
            ignored = item[4]

            trans_text = None
            if not ignored and content.strip():
                try:
                    trans_text = engine.translate(content)
                    time.sleep(0.3) 
                except Exception as e:
                    log.error(f"Error translating segment {item[0]}: {e}")
                    trans_text = "[Translation Failed]"
            
            if trans_text:
                paragraphs.append(Paragraph(content, trans_text))
            
            if not ignored:
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
        new_content = etree.tostring(page.data, encoding='utf-8', method='xml')
        page.item.set_content(new_content)

    # Sanitize TOC UIDs
    def fix_uid(toc_tree):
        for item in toc_tree:
            if isinstance(item, (list, tuple)):
                fix_uid(item)
            elif hasattr(item, 'uid') and not item.uid:
                item.uid = f'toc-{id(item)}'
    fix_uid(book.toc)

    # Translate TOC
    log.info("Translating Table of Contents...")
    def translate_toc(toc_tree):
        for item in toc_tree:
            if isinstance(item, (list, tuple)):
                translate_toc(item)
            elif hasattr(item, 'title') and item.title:
                try:
                    trans_title = engine.translate(item.title)
                    if trans_title:
                         item.title = trans_title
                    if not use_openrouter: time.sleep(0.3)
                except Exception:
                    pass
    
    translate_toc(book.toc)

    # Write output
    try:
        epub.write_epub(output_path, book)
        log.info(f"Success! Translated epub saved to: {output_path}")
    except Exception:
        log.error(f"Failed to write output epub: {traceback.format_exc()}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Translate English Epub to Italian")
    parser.add_argument('input_epub', help="Path to input epub file")
    parser.add_argument('-OPR', '--openrouter', action='store_true', help="Use OpenRouter engine")
    parser.add_argument('--model', type=str, help="OpenRouter model ID (e.g., google/gemini-flash-1.5)")
    parser.add_argument('--threads', type=int, default=8, help="Number of parallel threads for translation")
    args = parser.parse_args()
    process_epub(args.input_epub, use_openrouter=args.openrouter, model=args.model, threads=args.threads)
