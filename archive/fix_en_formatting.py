#!/usr/bin/env python3
"""Fix EN formatting — round 2: comprehensive strong/code/br/em additions."""

import json, re

HTML_PATH = "/Users/guoliwei/Downloads/workspace/bilingual-reader/html/LLM-Powered-Autonomous-Agents.html"

with open(HTML_PATH, 'r') as f:
    html = f.read()

m = re.search(r'var data = (\{.*?\n\});', html, re.DOTALL)
data = json.loads(m.group(1), strict=False)

fixes = 0

# --- STRONG: concept names that should be bold in EN ---
strong_map = {
    # Section: 规划
    'Chain of thought (CoT;': '<strong>Chain of thought</strong> (CoT;',
    'Tree of Thoughts (Yao': '<strong>Tree of Thoughts</strong> (Yao',
    'LLM+P (Liu': '<strong>LLM+P</strong> (Liu',
    'ReAct (Yao': '<strong>ReAct</strong> (Yao',
    'Reflexion (Shinn': '<strong>Reflexion</strong> (Shinn',
    'Chain of Hindsight (CoH;': '<strong>Chain of Hindsight</strong> (CoH;',
    'Algorithm Distillation (AD;': '<strong>Algorithm Distillation</strong> (AD;',
    # Section: 工具使用
    'MRKL (Karpas': '<strong>MRKL</strong> (Karpas',
    'Both TALM (Tool': '<strong>TALM</strong> (Tool',
    'and Toolformer (Schick': 'and <strong>Toolformer</strong> (Schick',
    'HuggingGPT (Shen': '<strong>HuggingGPT</strong> (Shen',
    'API-Bank (Li': '<strong>API-Bank</strong> (Li',
    # Section: 案例研究
    'ChemCrow (Bran': '<strong>ChemCrow</strong> (Bran',
    'Boiko et al. (2023)': '<strong>Boiko et al. (2023)</strong>',
    'Generative Agents (Park,': '<strong>Generative Agents</strong> (Park,',
    'AutoGPT has drawn': '<strong>AutoGPT</strong> has drawn',
    'GPT-Engineer is another': '<strong>GPT-Engineer</strong> is another',
    # Memory types (already have strong tags but check)
    'Explicit / declarative memory': '<em>Explicit / declarative memory</em>',
    'Implicit / procedural memory': '<em>Implicit / procedural memory</em>',
    # Sensory/STM/LTM
    'Sensory Memory as learning': '<strong>Sensory Memory</strong> as learning',
    'Short-term memory as in-context': '<strong>Short-term memory</strong> as in-context',
    'Long-term memory as the external': '<strong>Long-term memory</strong> as the external',
    # MIPS algorithm names in section 记忆
    'LSH (Locality-Sensitive': '<strong>LSH</strong> (Locality-Sensitive',
    'ANNOY (Approximate Nearest': '<strong>ANNOY</strong> (Approximate Nearest',
    'HNSW (Hierarchical Navigable': '<strong>HNSW</strong> (Hierarchical Navigable',
    'FAISS (Facebook AI': '<strong>FAISS</strong> (Facebook AI',
    'ScaNN (Scalable Nearest': '<strong>ScaNN</strong> (Scalable Nearest',
    # Section headings in case studies
    'ChemCrow (Bran': '<strong>ChemCrow</strong> (Bran',
}

# --- EM: italic terms ---
em_map = {
    'kybernetikos': '<em>kybernetikos</em>',
    'Explicit / declarative': '<em>Explicit / declarative',
    'Implicit / procedural': '<em>Implicit / procedural',
}

# --- BR: add <br> for multi-step lists ---
br_patterns = [
    # HuggingGPT 4 stages
    ('(1) Task planning: LLM works', '<br>(1) <strong>Task planning</strong>: LLM works'),
    ('(2) Model selection: LLM distributes', '<br>(2) <strong>Model selection</strong>: LLM distributes'),
    ('(3) Task execution: Expert models', '<br>(3) <strong>Task execution</strong>: Expert models'),
    ('(4) Response generation: LLM receives', '<br>(4) <strong>Response generation</strong>: LLM receives'),
    # API-Bank levels
    ('Level-1 evaluates', '<br>• <strong>Level-1</strong> evaluates'),
    ('Level-2 examines', '<br>• <strong>Level-2</strong> examines'),
    ('Level-3 assesses', '<br>• <strong>Level-3</strong> assesses'),
    # ChemCrow stages
    ('The LLM is provided with a list', '<br>The LLM is provided with a list'),
    ('It is then instructed', '<br>It is then instructed'),
    # HuggingGPT challenges
    ('(1) Efficiency improvement is needed', '<br>(1) Efficiency improvement is needed'),
    ('(2) It relies on a long context', '<br>(2) It relies on a long context'),
    ('(3) Stability improvement of LLM', '<br>(3) Stability improvement of LLM'),
]

for section in data['sections']:
    for pair in section['pairs']:
        en = pair.get('en', '')
        zh = pair.get('zh', '')
        if not en:
            continue

        # Apply strong replacements
        for old, new in strong_map.items():
            if old in en and new not in en:
                en = en.replace(old, new)
                fixes += 1

        # Apply em replacements
        for old, new in em_map.items():
            if old in en and new not in en:
                en = en.replace(old, new)
                fixes += 1

        # Apply br replacements
        for old, new in br_patterns:
            if old in en and new not in en:
                en = en.replace(old, new)
                fixes += 1

        pair['en'] = en

# Regenerate
data_json = json.dumps(data, ensure_ascii=False, indent=2)
new_block = f"var data = {data_json};"
new_html = re.sub(r'var data = \{.*?\n\};', new_block, html, flags=re.DOTALL)

with open(HTML_PATH, 'w') as f:
    f.write(new_html)

print(f"Fixed {fixes} formatting issues")
