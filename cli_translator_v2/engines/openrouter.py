
import json
import os
from .base import Base
from ..utils import log

class OpenRouter(Base):
    name = 'OpenRouter'
    alias = 'openrouter'
    endpoint = 'https://openrouter.ai/api/v1/chat/completions'
    
    # Prompt and settings
    system_prompt = """Sei un traduttore letterario esperto dall'inglese all'italiano, con profonda conoscenza della letteratura anglosassone (fiction come romanzi, poesie, racconti; non fiction come saggi, memoir, articoli storici o scientifici). Il tuo obiettivo è produrre traduzioni accurate, fluide e idiomatiche che preservino:

- Fedeltà semantica: Mantieni il significato esatto, senza aggiungere, omettere o interpretare liberamente. Se una parola ha ambiguità, scegli il senso contestuale più probabile e nota brevemente se rilevante.
- Stile e tono originale: Riproduci ritmo, registri (formale, colloquiale, poetico), figure retoriche (metafore, allitterazioni, ironia), voce narrativa (prima persona, onnisciente) e atmosfera emotiva. Per fiction, conserva il flusso narrativo; per non fiction, la precisione argomentativa e oggettività.
- Italiano naturale e letterario: Usa un italiano colto, elegante e idiomatico, evitando calchi dall'inglese (es. non "realizzare" per "realize" se non appropriato; preferisci "rendersi conto"). Rispetta norme grammaticali italiane (accordo genere/numero, congiuntivo, tempi verbali).
- Elementi culturali: Traduci nomi propri, luoghi e riferimenti storici fedelmente (es. "Baker Street" resta così, non "Via del Fornaio"); spiega brevemente in nota se un riferimento è oscuro per il pubblico italiano.
- Lunghezza e struttura: Mantieni paragrafi, dialoghi e capitoli invariati. Non riassumere o espandere.

Processo di traduzione passo-passo:
1. Leggi l'intero testo inglese.
2. Identifica genere (fiction/non fiction), tono, pubblico target e contesto.
3. Traduci frase per frase, rileggendo per coerenza stilistica.
4. Confronta con l'originale: verifica accuratezza semantica (100%), idiomaticità (alta) e musicalità.
5. Output: Solo la traduzione italiana pura, senza introduzioni.

Esempi di errori da evitare:
- Inglese: "He broke into a run." → Non "Entrò in una corsa", ma "Si mise a correre".
- Fiction poetica: "The heart wants what it wants." → "Il cuore vuole ciò che vuole" (preserva ritmo).

Rispondi solo con la traduzione richiesta."""

    model = "openai/gpt-oss-120b"
    
    def __init__(self, model=None):
        super().__init__()
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
             log.error("OPENROUTER_API_KEY not found in environment variables.")
        if model:
            self.model = model

    def get_headers(self):
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://github.com/vigliafg/Ebook-Translator-Calibre-Plugin', 
            'X-Title': 'Ebook-Translator-Calibre-Plugin',
        }

    def get_body(self, content):
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": content}
        ]
        
        data = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 8192
        }
        
        # Only add reasoning_effort for 'thinking' models or if explicitly requested.
        # For now, keep it 'low' if it's the default model or contains 'gpt-oss' or 'o1'
        if "gpt-oss" in self.model or "o1" in self.model:
            data["reasoning_effort"] = "low"
        
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

    # Optimization: Process multiple segments in one request to maximize context usage
    def translate_batch(self, segments):
        # We use a dictionary structure with IDs to ensure the model maintains 1-to-1 mapping.
        # This prevents "count mismatch" errors if the model hallucinates or splits items.
        
        to_translate = {str(i): seg for i, seg in enumerate(segments)}
        
        # Refined prompt for ID-mapped JSON batching
        batch_system_prompt = self.system_prompt + "\n\nCRITICAL: Return a JSON object where each key corresponds to the input ID and the value is the translated string. Return ONLY the JSON object. Example: {\"0\": \"traduzione 1\", \"1\": \"traduzione 2\"}"
        
        messages = [
            {"role": "system", "content": batch_system_prompt},
            {"role": "user", "content": json.dumps(to_translate, ensure_ascii=False)}
        ]
        
        data = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 8192,
            "reasoning_effort": "low"
        }
        
        from ..utils import request, log
        
        try:
            params = {
                'url': self.endpoint,
                'data': json.dumps(data),
                'headers': self.get_headers(),
                'method': 'POST',
                'timeout': 180, 
            }
            response = request(**params)
            
            result_text = self.get_result(response)
            if not result_text:
                log.error("Batch request returned no result text.")
                return None
                
            # Parse the JSON from the model
            try:
                # Robust extraction of JSON from model output
                clean_json = result_text
                if "```json" in clean_json:
                    clean_json = clean_json.split("```json")[1].split("```")[0].strip()
                elif "```" in clean_json:
                    clean_json = clean_json.split("```")[1].split("```")[0].strip()
                else:
                    start_idx = clean_json.find('{')
                    end_idx = clean_json.rfind('}')
                    if start_idx != -1 and end_idx != -1:
                        clean_json = clean_json[start_idx:end_idx+1]
                
                translated_data = json.loads(clean_json)
                
                # Map back to a list by index to ensure order
                results = []
                missing = []
                for i in range(len(segments)):
                    idx_str = str(i)
                    if idx_str in translated_data:
                        results.append(str(translated_data[idx_str]).strip())
                    else:
                        missing.append(idx_str)
                
                if not missing:
                    return results
                else:
                    log.error(f"Batch missing IDs: {', '.join(missing)}. Content: {result_text[:200]}...")
            except Exception as e:
                log.error(f"Failed to parse JSON batch response: {e}. Content: {result_text[:200]}...")
                
        except Exception as e:
            log.error(f"Batch request failed: {e}")
            
        return None
