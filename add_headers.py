#!/usr/bin/env python3
"""
Script to add copyright headers to Python files.
"""

import os
from datetime import datetime

HEADER = """# Copyright (c) {} Leonardo Marques Rocha
# All rights reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, modification, public performance, or public display of the
# materials, via any medium is strictly prohibited.
""".format(datetime.now().year)

def add_header_to_file(filepath):
    """Add header to a single file if it doesn't already have one."""
    with open(filepath, 'r+', encoding='utf-8') as f:
        content = f.read()
        
        # Skip if header already exists
        if 'Copyright (c)' in content[:500]:  # Check first 500 chars for existing header
            print(f"Skipping {filepath} - header already exists")
            return
            
        # Add header
        f.seek(0, 0)
        f.write(HEADER + '\n\n' + content)
        print(f"Added header to {filepath}")

def main():
    """Find all Python files and add headers."""
    for root, _, files in os.walk('.'):
        for file in files:
            if file.endswith('.py') and not file.startswith('add_headers'):
                filepath = os.path.join(root, file)
                add_header_to_file(filepath)

if __name__ == "__main__":
    main()
