#!/usr/bin/env python3

# -----------------------------------------------------------------------------
# clean-text.py - Text Normalizer
# Strips trailing unicode whitespace (regex \s+$) and enforces double-newline 
# spacing between non-empty lines. Useful for cleaning web-scraped content.
# -----------------------------------------------------------------------------

import sys
import re
from pathlib import Path

def clean_file(file_path):
    path = Path(file_path)
    if not path.exists():
        print(f"Error: File {file_path} not found.")
        return

    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Split by newlines to process line by line
        lines = content.splitlines()

        cleaned_lines = []
        for line in lines:
            # Regex \s matches [ \t\n\r\f\v] and unicode spaces like \xa0
            # We remove them from the right side ($)
            clean_line = re.sub(r'\s+$', '', line)
            
            # Skip empty lines to prevent excessive gaps
            if clean_line:
                cleaned_lines.append(clean_line)

        # Join with double newline to enforce paragraph spacing
        output_content = '\n\n'.join(cleaned_lines)
        
        # Save as new file
        output_path = path.with_name(f"{path.stem}_cleaned{path.suffix}")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output_content)

        print(f"Done. Cleaned file saved to: {output_path}")

    except Exception as e:
        print(f"Error processing file: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <filename>")
    else:
        clean_file(sys.argv[1])