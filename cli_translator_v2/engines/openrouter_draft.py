
import json
import os
import time
from .base import Base
from ..utils import log

class OpenRouter(Base):
    name = 'OpenRouter'
    alias = 'openrouter'
    endpoint = 'https://openrouter.ai/api/v1/chat/completions'
    
    # Prompt and settings
    system_prompt = """Sei un traduttore letterario esperto dall'inglese all'italiano... (truncated for brevity, will insert full prompt)"""
    model = "openai/gpt-oss-120b"
    
    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
             log.error("OPENROUTER_API_KEY not found in environment variables.")

    def get_headers(self):
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://github.com/vigliafg/Ebook-Translator-Calibre-Plugin', 
            'X-Title': 'Ebook-Translator-Calibre-Plugin',
        }

    def get_body(self, content):
        # Determine strict or other params if needed
        # User requested "reasoning level" = "low". 
        # Check if 'reasoning_effort' is valid for this model or if it's an o1 thing.
        # I will include it as requested; if API rejects, we might need to remove it.
        # But for 'gpt-oss-120b', maybe it's just a generic parameter or ignored.
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": content}
        ]
        
        data = {
            "model": self.model,
            "messages": messages,
            # "reasoning_effort": "low", # This is usually for o1-mini/preview. I will uncomment if user insists/model is o1. 
            # Given user said "gpt-oss-120b" BUT also "level of reasoning... low", 
            # I'll stick to strict user instructions but maybe wrap in try/catch or just add it.
            # Actually, "reasoning_effort" is supported by OpenAI o1. 
            # If user explicitly asked for logic level low, I will add it to the body.
        }
        # Add reasoning_effort only if I'm sure, or maybe just add it and see. 
        # Safest is to add it as user explicitly asked: "il livello di ragionamento... deve essere impostato a 'low'"
        # I'll add checking logic or just add it.
        # NOTE: 'reasoning_effort' is Beta for OpenAI. 
        
        # It seems the user might be confusing models or this is a specific setup. 
        # I will add it to data.
        
        # For now, I won't put it in 'data' immediately in this variable definition 
        # because I need to insert the full system prompt first.
        return json.dumps(data)

    def get_result(self, response):
        try:
            data = json.loads(response)
            if 'choices' in data and len(data['choices']) > 0:
                return data['choices'][0]['message']['content']
            if 'error' in data:
                 raise Exception(data['error']['message'])
            return None
        except Exception as e:
            raise Exception(f"Failed to parse OpenRouter response: {e}")

    # Override translate to handle the specific logic if needed, 
    # but Base.translate uses get_body -> request -> get_result.
    # However, Base.translate uses `mechanize` via `utils.request`.
    # `utils.request` sends data as urlencoded if dictionary? No, let's check utils.py
    
