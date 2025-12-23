
import sys
import os

# Add the parent directory to sys.path to allow package imports
parent_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(parent_dir))

if __name__ == "__main__":
    from cli_translator_v2.console import process_epub
    import argparse
    
    parser = argparse.ArgumentParser(description="Translate English Epub to Italian (v2 with OpenRouter support)")
    parser.add_argument('input_epub', help="Path to input epub file")
    parser.add_argument('-OPR', '--openrouter', action='store_true', help="Use OpenRouter engine")
    args = parser.parse_args()
    
    process_epub(args.input_epub, use_openrouter=args.openrouter)
