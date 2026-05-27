#!/usr/bin/env python3
"""Embed data-agent.json into html/LLM-Powered-Autonomous-Agents.html"""

import json, re, os

BASE = os.path.expanduser("~/Downloads/workspace/bilingual-reader")

# Read the JSON data
with open(f"{BASE}/data-agent.json", 'r', encoding='utf-8') as f:
    data = json.load(f)

# Read the HTML template
html_path = f"{BASE}/html/LLM-Powered-Autonomous-Agents.html"
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

# Build the new data block
data_json = json.dumps(data, ensure_ascii=False, indent=2)
new_block = f"var data = {data_json};"

# Replace the var data = {...} block
# The pattern: starts with "var data = {" and ends with "};\ndocument.title=data.title;"
pattern = r'var data = \{.*?\n\};'
replacement = new_block

# Use regex to find and replace
new_html, count = re.subn(pattern, replacement, html, flags=re.DOTALL)

if count == 1:
    print(f"Successfully replaced data block (1 occurrence)")
elif count == 0:
    print("ERROR: Could not find data block to replace!")
    # Debug: find the position
    idx = html.find('var data = {')
    if idx >= 0:
        print(f"  Found 'var data = {{' at position {idx}")
        # Find the closing };
        end_idx = html.find('document.title=data.title;', idx)
        if end_idx >= 0:
            print(f"  Found 'document.title=data.title;' at position {end_idx}")
    exit(1)
else:
    print(f"WARNING: Replaced {count} occurrences, expected 1")

# Write back
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(new_html)

print(f"Updated: {html_path}")

# Validate the result by re-reading the JSON file and comparing
# (avoid parsing from HTML which can have regex issues)
with open(f"{BASE}/data-agent.json", 'r', encoding='utf-8') as f:
    recheck = json.load(f)

print(f"\nRe-validated data-agent.json")
print(f"  Title: {recheck['title'][:60]}...")
print(f"  Sections: {len(recheck['sections'])}")
total = sum(len(s['pairs']) for s in recheck['sections'])
total_en = sum(1 for s in recheck['sections'] for p in s['pairs'] if p['en'].strip())
print(f"  Total pairs: {total}")
print(f"  EN coverage: {total_en}/{total} ({total_en/total*100:.0f}%)")

# Quick check that the HTML contains the data
with open(html_path, 'r', encoding='utf-8') as f:
    updated_html = f.read()
if 'var data = {' in updated_html and '"title": "LLM 驱动的自主 Agent' in updated_html:
    print("\nHTML contains embedded data block: OK")
else:
    print("\nWARNING: HTML may not contain the data block properly!")

print("\nDone!")
