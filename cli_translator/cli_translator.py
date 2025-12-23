#!/usr/bin/env python3
import re
import os
import sys
import ssl
import time
import json
import socket
import hashlib
import logging
import argparse
import traceback
import copy
from types import ModuleType
from typing import Generator, Any
from subprocess import Popen, PIPE
from contextlib import contextmanager
from html import unescape
from xml.sax.saxutils import escape as xml_escape
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- THIRD PARTY IMPORTS ---
try:
    import ebooklib
    from ebooklib import epub
    from lxml import etree
    from mechanize import Browser, Request, HTTPError
    from mechanize._response import response_seek_wrapper as Response
    from cssselect import GenericTranslator, SelectorError
except ImportError as e:
    print(f"Error: Missing dependency '{e.name}'.")
    print("Please install requirements: pip install ebooklib lxml mechanize cssselect PySocks")
    sys.exit(1)

# Optional SOCKS support
try:
    import socks
except ImportError:
    socks = None

# --- CONSTANTS & LOGGING ---
ns = {'x': 'http://www.w3.org/1999/xhtml'}
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger('cli_v3')

# --- SECTION: EXCEPTIONS ---
class EbookTranslatorError(Exception): pass
class UnexpectedResult(EbookTranslatorError): pass
class ConversionAbort(EbookTranslatorError): pass
class TranslationFailed(EbookTranslatorError): pass

# --- SECTION: UTILS ---
def sep(char='═', count=38): return char * count

def trim(text):
    text = re.sub(u'\u00a0|\u3000', ' ', text)
    text = re.sub(u'\u200b|\ufeff', '', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'(?![\n\r\t])[\x00-\x1f\x7f-\xa0\xad]', '', text)
    return text.strip()

def uid(*args):
    md5 = hashlib.md5()
    for arg in args:
        md5.update(arg if isinstance(arg, bytes) else arg.encode('utf-8'))
    return md5.hexdigest()

def sorted_mixed_keys(s):
    return [int(v) if v.isdigit() else v for v in re.split(r'(\d+)', s)]

def css_to_xpath(selectors):
    patterns = []
    if isinstance(selectors, str): selectors = [selectors]
    for s in selectors:
        try:
            patterns.append(GenericTranslator().css_to_xpath(s, prefix='self::x:'))
        except (SelectorError, Exception): pass
    return patterns

def create_xpath(selectors):
    rules = css_to_xpath(selectors)
    if not rules: return ".//*" 
    return './/*[%s]' % ' or '.join(rules)

def request(url, data=None, headers={}, method='GET', timeout=60, proxy_uri=None, raw_object=False):
    br = Browser()
    br.set_handle_robots(False)
    try:
        ctx = ssl._create_unverified_context(cert_reqs=ssl.CERT_NONE)
        br.set_ca_data(context=ctx)
    except: pass
    if proxy_uri:
        br.set_proxies({'http': proxy_uri, 'https': proxy_uri})
    if data is not None and isinstance(data, str):
        data = data.encode('utf-8')
    try:
        req = Request(url, data, headers=headers, timeout=timeout, method=method)
        br.open(req)
        resp = br.response()
        if resp is None or raw_object: return resp
        return resp.read().decode('utf-8').strip()
    except Exception as e:
        raise Exception(f"Request failed: {e}")

# --- SECTION: CONFIG ---
def get_config():
    return {
        'translation_position': 'below', # usually overridden by handler
        'merge_enabled': False,
        'priority_rules': ['p', 'pre', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote'],
        'rule_mode': 'normal',
        'filter_scope': 'content',
        'element_rules': [],
        'reserve_rules': [],
    }

# --- SECTION: LANGUAGES ---
google_languages = {
    'English': 'en', 'Italian': 'it', 'French': 'fr', 'German': 'de', 'Spanish': 'es', 
    'Japanese': 'ja', 'Chinese (Simplified)': 'zh-CN', 'Russian': 'ru'
}

# --- SECTION: BASE ENGINE ---
class BaseEngine:
    name = None
    lang_codes = {'source': google_languages, 'target': google_languages}
    
    def __init__(self):
        self.source_lang = "English"
        self.target_lang = "Italian"
        self.api_key = None
        self.request_attempt = 3
        self.request_timeout = 60

    def set_source_lang(self, l): self.source_lang = l
    def set_target_lang(self, l): self.target_lang = l
    def _get_source_code(self): return self.lang_codes['source'].get(self.source_lang, 'en')
    def _get_target_code(self): return self.lang_codes['target'].get(self.target_lang, 'it')
    def get_target_lang(self): return self.target_lang
    def translate(self, content): raise NotImplementedError()

class GoogleFreeTranslateNew(BaseEngine):
    name = 'Google(Free)New'
    endpoint = 'https://translate-pa.googleapis.com/v1/translate'
    
    def translate(self, text):
        import urllib.parse
        params = {
            'params.client': 'gtx',
            'query.source_language': self._get_source_code(),
            'query.target_language': self._get_target_code(),
            'data_types': 'TRANSLATION',
            'key': 'AIzaSyDLEeFI5OtFBwYBIoK_jj5m32rZK5CkCXA',
            'query.text': text,
        }
        url = self.endpoint + "?" + urllib.parse.urlencode(params)
        resp = request(url, method='GET')
        return json.loads(resp)['translation']

class OpenRouter(BaseEngine):
    name = 'OpenRouter'
    endpoint = 'https://openrouter.ai/api/v1/chat/completions'
    
    system_prompt = """Sei un traduttore esperto dall'inglese all'italiano, specializzato in letteratura, saggi tecnici e divulgazione scientifica (medicina, fisica, matematica, biologia, informatica). Il tuo obiettivo è la massima qualità formale e contenutistica:

1. GENERE LETTERARIO (Narrativa):
- Traduzione fluida, colta ed evocativa. Preserva stile, tono e figure retoriche.
- Usa un italiano idiomatico ed elegante (es. "Si mise a correre" e non "Ruppe in una corsa").

2. TESTI TECNICI E MANUALISTICA:
- Priorità assoluta: PRECISIONE TERMINOLOGICA e NOMENCLATURA standard.
- Stile asciutto, oggettivo e univoco. Evita sinonimi creativi per concetti tecnici: la coerenza è vitale.
- Dati: Valori numerici, unità di misura, formule matematiche e codici devono restare identici.

3. DIVULGAZIONE SCIENTIFICA (Saggistica per il pubblico):
- Bilancia rigore e leggibilità. Sii preciso nei termini scientifici ma chiaro nell'esposizione.
- Mantieni lo spirito didattico e il tono autorevole ma accessibile dell'autore.

REGOLE UNIVERSALI:
- SEMANTICA (100%): Non aggiungere, omettere o alterare il significato originale.
- FORMATO: Rispetta rigorosamente paragrafi, dialoghi e tag (come {{id_00001}}).
- OUTPUT: Solo la traduzione italiana pura, senza commenti o introduzioni.

Processo: Identifica il tipo di testo (es. un saggio di fisica quantistica vs un romanzo storico) e adatta il registro. Rispondi solo con la traduzione."""

    def __init__(self, model=None):
        super().__init__()
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.model = model or "openai/gpt-oss-120b"
        if not self.api_key: log.error("OPENROUTER_API_KEY environment variable not set.")

    def get_headers(self):
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://github.com/vigliafg/Ebook-Translator-Calibre-Plugin',
            'X-Title': 'cli_translator_v3'
        }

    def translate(self, text):
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"Translate the following text to Italian. Return ONLY the translation, absolutely no explanations or labels:\n\n{text}"}
            ]
        }
        if any(m in self.model for m in ["gpt-oss", "o1"]): data["reasoning_effort"] = "low"
        
        try:
            resp_str = request(self.endpoint, data=json.dumps(data), headers=self.get_headers(), method='POST')
            res_data = json.loads(resp_str)
            translated_text = res_data['choices'][0]['message']['content'].strip()
            # Basic sanitization for models that ignore instructions
            translated_text = re.sub(r'^(translation|result|output|traduzione|italian)[:\s\-]+', '', translated_text, flags=re.IGNORECASE)
            translated_text = translated_text.strip().strip('"').strip("'").strip()
            return translated_text
        except Exception as e:
            log.warning(f"Translation failed for '{text[:20]}...': {e}")
            return text

    def translate_batch(self, segments):
        to_translate = {str(i): seg for i, seg in enumerate(segments)}
        batch_system_prompt = self.system_prompt + "\n\nCRITICAL: Return a JSON object with input IDs as keys and translations as values. ONLY JSON. Example: {\"0\": \"...\", \"1\": \"...\"}"
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": batch_system_prompt},
                {"role": "user", "content": json.dumps(to_translate, ensure_ascii=False)}
            ],
            "max_tokens": 8192,
            "reasoning_effort": "low"
        }
        
        try:
            resp = request(self.endpoint, data=json.dumps(data), headers=self.get_headers(), method='POST', timeout=180)
            res_json = json.loads(resp)
            if 'choices' not in res_json: return None
            result_text = res_json['choices'][0]['message']['content']
            
            # Robust JSON extraction
            clean_json = result_text
            if "```json" in clean_json: clean_json = clean_json.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_json: clean_json = clean_json.split("```")[1].split("```")[0].strip()
            else:
                s, e = clean_json.find('{'), clean_json.rfind('}')
                if s != -1 and e != -1: clean_json = clean_json[s:e+1]
            
            translated_data = json.loads(clean_json)
            return [str(translated_data.get(str(i), "")).strip() for i in range(len(segments))]
        except Exception as e:
            log.error(f"Batch failed: {e}")
            return None

# --- SECTION: ELEMENT HANDLING ---
class Element:
    def __init__(self, element, page_id=None, ignored=False):
        self.element = element
        self.page_id = page_id
        self.ignored = ignored
        self.placeholder = ()
        self.position = 'only'
        self.reserve_elements = []

    def get_text(self): return trim(''.join(self.element.itertext()))
    def get_raw(self): return etree.tostring(self.element, encoding='utf-8', with_tail=False).decode('utf-8')
    def get_content(self): return self.get_text()

    def add_translation(self, translation=None):
        if translation is not None and not self.ignored:
            # Simplistic for V3: replace text, keep tag
            new_el = copy.deepcopy(self.element)
            new_el.text = translation
            for child in list(new_el): new_el.remove(child)
            self.element.getparent().replace(self.element, new_el)
            self.element = new_el

class PageElement(Element):
    pass

class Extraction:
    def __init__(self, pages, priority_rules, filter_rules, ignore_rules):
        self.pages = pages
        self.priority_patterns = css_to_xpath(['p', 'pre', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote'] + priority_rules)
        self.ignore_patterns = css_to_xpath(['pre', 'code'] + ignore_rules)

    def get_elements(self):
        elements = []
        for page in self.pages:
            body = page.data.find('.//x:body', namespaces=ns)
            if body is None: body = page.data.find('.//body')
            if body is not None:
                self.extract_recursive(page.id, body, elements)
        return elements

    def extract_recursive(self, page_id, root, elements):
        for el in root.findall('./*'):
            if any(el.xpath(p, namespaces=ns) for p in self.ignore_patterns):
                elements.append(PageElement(el, page_id, True))
                continue
            
            has_text = el.text and el.text.strip()
            is_priority = any(el.xpath(p, namespaces=ns) for p in self.priority_patterns)
            
            if has_text or is_priority:
                elements.append(PageElement(el, page_id))
            else:
                self.extract_recursive(page_id, el, elements)

class ElementHandler:
    def __init__(self, placeholder, separator, position):
        self.placeholder = placeholder
        self.separator = separator
        self.position = position
        self.elements = {}

    def prepare_original(self, elements):
        originals = []
        for oid, el in enumerate(elements):
            if not el.ignored: self.elements[oid] = el
            originals.append((oid, uid(str(oid), el.get_content()), el.get_raw(), el.get_content(), el.ignored, None, el.page_id))
        return originals

    def add_translations(self, results):
        # results: list of (orig_text, trans_text)
        trans_map = {r[0]: r[1] for r in results}
        for oid, el in self.elements.items():
            content = el.get_content()
            if content in trans_map:
                el.add_translation(trans_map[content])

# --- SECTION: MAIN ENGINE ---
def process_epub(input_path, use_opr=False, model=None, threads=8):
    if not os.path.exists(input_path): return log.error("File not found.")
    output_path = input_path.rsplit('.', 1)[0] + '_ITALIANO.epub'
    
    book = epub.read_epub(input_path)
    engine = OpenRouter(model=model) if use_opr else GoogleFreeTranslateNew()
    
    wrapped_pages = []
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        try:
            tree = etree.fromstring(item.get_content(), parser=etree.XMLParser(recover=True))
            page = type('Page', (), {'id': item.file_name, 'href': item.file_name, 'data': tree, 'item': item})
            wrapped_pages.append(page)
        except: pass

    ext = Extraction(wrapped_pages, [], [], [])
    elements = ext.get_elements()
    handler = ElementHandler(None, '\n\n', 'only')
    originals = handler.prepare_original(elements)
    
    valid_items = [o for o in originals if not o[4] and o[3].strip()]
    log.info(f"Translating {len(valid_items)} segments...")

    final_results = []
    start_time = time.time()
    
    if use_opr and hasattr(engine, 'translate_batch'):
        batches = [valid_items[i:i+20] for i in range(0, len(valid_items), 20)]
        
        def run_batch(b_info):
            idx, b = b_info
            res = engine.translate_batch([item[3] for item in b])
            if not res: 
                log.warning(f"Batch {idx} failed, fallback...")
                res = [engine.translate(item[3]) for item in b]
            return [(item[3], r) for item, r in zip(b, res)]

        with ThreadPoolExecutor(max_workers=threads) as exec:
            futs = {exec.submit(run_batch, (i, b)): i for i, b in enumerate(batches)}
            for f in as_completed(futs):
                batch_res = f.result()
                final_results.extend(batch_res)
                log.info(f"Progress: {len(final_results)}/{len(valid_items)} ({(len(final_results)/(time.time()-start_time)):.1f} s/s)")
    else:
        for i, it in enumerate(valid_items):
            final_results.append((it[3], engine.translate(it[3])))
            if i % 10 == 0: log.info(f"Progress: {i}/{len(valid_items)}")

    handler.add_translations(final_results)
    
    for page in wrapped_pages:
        page.item.set_content(etree.tostring(page.data, encoding='utf-8', method='xml'))
    
    # Sanitize TOC UIDs
    def fix_uid(toc_tree):
        for item in toc_tree:
            if isinstance(item, (list, tuple)):
                fix_uid(item)
            elif hasattr(item, 'uid') and not item.uid:
                item.uid = f'toc-{id(item)}'
    
    fix_uid(book.toc)
    
    # Translate TOC
    log.info("Translating TOC...")
    toc_items = []
    def collect_toc(toc_tree):
        for item in toc_tree:
            if isinstance(item, (list, tuple)):
                collect_toc(item)
            elif hasattr(item, 'title'):
                toc_items.append(item)
    
    collect_toc(book.toc)
    
    if toc_items:
        titles = [it.title for it in toc_items]
        translated_titles = []
        if use_opr and hasattr(engine, 'translate_batch'):
            for i in range(0, len(titles), 20):
                batch = titles[i:i+20]
                res = engine.translate_batch(batch)
                if not res: 
                    log.warning(f"TOC Batch {i//20} failed, fallback...")
                    res = []
                    for t in batch:
                        try: res.append(engine.translate(t))
                        except: res.append(t)
                translated_titles.extend(res)
        else:
            translated_titles = [engine.translate(t) for t in titles]
            
        for item, trans in zip(toc_items, translated_titles):
            item.title = trans
            
    epub.write_epub(output_path, book)
    log.info(f"Success! Saved to {output_path}")

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('input')
    p.add_argument('-OPR', action='store_true')
    p.add_argument('--model')
    p.add_argument('--threads', type=int, default=8)
    args = p.parse_args()
    process_epub(args.input, args.OPR, args.model, args.threads)
