import os
import sys
import time
import json
from html import unescape
from subprocess import Popen, PIPE
from http.client import IncompleteRead

from ..utils import request, traceback_error

from .base import Base
from .languages import google


class GoogleFreeTranslateNew(Base):
    name = 'Google(Free)New'
    alias = 'Google (Free) - New'
    free = True
    lang_codes = Base.load_lang_codes(google)
    endpoint = 'https://translate-pa.googleapis.com/v1/translate'
    need_api_key = False

    def get_headers(self):
        return {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 '
            'Safari/537.36',
        }

    def get_body(self, text):
        self.method = 'GET'
        return {
            'params.client': 'gtx',
            'query.source_language': self._get_source_code(),
            'query.target_language': self._get_target_code(),
            'query.display_language': 'en-US',
            'data_types': 'TRANSLATION',
            # 'data_types': 'SENTENCE_SPLITS',
            # 'data_types': 'BILINGUAL_DICTIONARY_FULL',
            'key': 'AIzaSyDLEeFI5OtFBwYBIoK_jj5m32rZK5CkCXA',
            'query.text': text,
        }

    def get_result(self, response):
        return json.loads(response)['translation']


class GoogleFreeTranslateHtml(Base):
    name = 'Google(Free)Html'
    alias = 'Google (Free) - HTML'
    free = True
    lang_codes = Base.load_lang_codes(google)
    endpoint = 'https://translate-pa.googleapis.com/v1/translateHtml'
    need_api_key = False
    support_html = True

    def get_headers(self):
        return {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/json+protobuf',
            'X-Goog-Api-Key': 'AIzaSyATBXajvzQLTDHEQbcpq0Ihe0vWDHmO520',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 '
            'Safari/537.36',
        }

    def get_body(self, text):
        return json.dumps([
            [
                [text],
                self._get_source_code(),
                self._get_target_code()
            ],
            "wt_lib"
        ])

    def get_result(self, response):
        return json.loads(response)[0][0]


class GoogleFreeTranslate(Base):
    name = 'Google(Free)'
    alias = 'Google (Free) - Old'
    free = True
    lang_codes = Base.load_lang_codes(google)
    endpoint = 'https://translate.googleapis.com/translate_a/single'
    need_api_key = False

    def get_headers(self):
        return {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'DeepLBrowserExtension/1.3.0 Mozilla/5.0 (Macintosh;'
            ' Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)'
            ' Chrome/111.0.0.0 Safari/537.36',
        }

    def get_body(self, text):
        # The POST method is unstable, despite its ability to send more text.
        # However, it can be used occasionally with an unacceptable length.
        self.method = 'GET' if len(text) <= 1800 else 'POST'
        return {
            'client': 'gtx',
            'sl': self._get_source_code(),
            'tl': self._get_target_code(),
            'dt': 't',
            'dj': 1,
            'q': text,
        }

    def get_result(self, response):
        # return ''.join(i[0] for i in json.loads(data)[0])
        return ''.join(i['trans'] for i in json.loads(response)['sentences'])
