import os
import sys
import json

# Add project root to sys.path
sys.path.append(os.getcwd())

from cli_translator_v2.engines.openrouter import OpenRouter

def test_diagnostic():
    # Use DeepSeek V3 as requested
    engine = OpenRouter(model="deepseek/deepseek-chat")
    
    segments = [
        "In a hole in the ground there lived a hobbit.",
        "It was a bright cold day in April, and the clocks were striking thirteen.",
        "He was an old man who fished alone in a skiff in the Gulf Stream.",
        "Call me Ishmael.",
        "All happy families are alike; each unhappy family is unhappy in its own way.",
        "It was the best of times, it was the worst of times.",
        "The sun shone, having no alternative, on the nothing new.",
        "A screaming comes across the sky.",
        "I am an invisible man.",
        "Somewhere in la Mancha, in a place whose name I do not care to remember, a gentleman lived not long ago."
    ]
    
    print(f"Testing DeepSeek Batch with {len(segments)} segments...")
    results = engine.translate_batch(segments)
    
    if results:
        print(f"Success! Got {len(results)} translations.")
        for i, res in enumerate(results):
            print(f"[{i}] {res}")
    else:
        print("Batch Failed.")

if __name__ == "__main__":
    test_diagnostic()
