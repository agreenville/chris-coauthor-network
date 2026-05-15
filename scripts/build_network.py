import docx
import re
import json
from collections import defaultdict
import itertools

doc = docx.Document(ROOT / 'Chris_pubs.docx')
paragraphs = [p.text.strip() for p in doc.paragraphs]

SECTIONS_TO_PARSE = {
    'Books and journal theme issues': (2, 57),
    'Monographs': (57, 94),
    'Scientific articles': (148, 1045),
    'Chapters in books': (1045, 1330),
}

def join_paragraphs(paras):
    joined = []
    current = ""
    for p in paras:
        if not p:
            if current:
                joined.append(current)
                current = ""
            continue
        if re.match(r'^[A-Z][a-zA-Záéíóúüñ\-\']+,\s+[A-Z]', p):
            if current:
                joined.append(current)
            current = p
        else:
            if current:
                current = current + " " + p
            else:
                current = p
    if current:
        joined.append(current)
    return joined

def extract_authors(ref_text):
    year_match = re.search(r'\s*[\(\[]?\s*(1[89]\d\d|20[012]\d)\s*[\)\]]?\s*[a-z]?\s*[,\.]', ref_text)
    if not year_match:
        return []
    author_block = ref_text[:year_match.start()].strip()
    author_block = author_block.replace(' & ', ' and ').replace('& ', ' and ')
    parts = re.split(r'\s+and\s+', author_block)
    authors = []
    for part in parts:
        part = part.strip().rstrip(',').strip()
        if not part:
            continue
        for m in re.finditer(
            r'([A-Z][a-zA-Záéíóúüñ\-\']+(?:\s+[a-z]+\s+[A-Z][a-zA-Záéíóúüñ\-\']+)?)'
            r',\s*'
            r'([A-Z](?:\.[A-Z])*\.(?:\s*[A-Z]\.)*(?:\s*[A-Z]-[A-Z]\.)?)',
            part
        ):
            lastname = m.group(1).strip()
            initials = m.group(2).strip()
            authors.append(f"{lastname}, {initials}")
    return authors

CHRIS = "Dickman, C. R."

all_refs = []
for section, (start, end) in SECTIONS_TO_PARSE.items():
    paras = paragraphs[start:end]
    refs = join_paragraphs(paras)
    for ref in refs:
        authors = extract_authors(ref)
        if authors and any('Dickman' in a for a in authors):
            all_refs.append({'section': section, 'authors': authors})

# Name normalisation: merge "Lastname, A." with "Lastname, A. B." -> keep longer form
# Build a map: (lastname, first_initial) -> canonical name
def get_last_first(name):
    parts = name.split(',', 1)
    if len(parts) < 2:
        return name, ''
    last = parts[0].strip()
    inits = parts[1].strip()
    first_init = inits[0] if inits else ''
    return last, first_init

# First pass: collect all names
all_names_raw = set()
for entry in all_refs:
    for a in entry['authors']:
        all_names_raw.add(a)

# Build canonical: for each (lastname, first_init), keep longest initials string
from collections import defaultdict
canon_map = {}
groups = defaultdict(list)
for name in all_names_raw:
    last, fi = get_last_first(name)
    groups[(last, fi)].append(name)

for key, names in groups.items():
    canonical = max(names, key=lambda x: len(x))
    for n in names:
        canon_map[n] = canonical

# Also handle Dickman variants
for name in list(canon_map.keys()):
    if 'Dickman' in name and 'C.' in name:
        canon_map[name] = CHRIS

# Re-process with canonical names
chris_coauth_count = defaultdict(int)
pairwise_count = defaultdict(int)
author_pub_count = defaultdict(int)

for entry in all_refs:
    raw_authors = entry['authors']
    norm_authors = list(dict.fromkeys([canon_map.get(a, a) for a in raw_authors]))
    
    for a in norm_authors:
        author_pub_count[a] += 1
    
    if CHRIS in norm_authors:
        others = [a for a in norm_authors if a != CHRIS]
        for a in others:
            chris_coauth_count[a] += 1
        for a, b in itertools.combinations(sorted(norm_authors), 2):
            pairwise_count[(a, b)] += 1

print(f"Total refs: {len(all_refs)}")
print(f"Total co-authors: {len(chris_coauth_count)}")
print(f"Top 10: {sorted(chris_coauth_count.items(), key=lambda x: -x[1])[:10]}")

# Save for use in visualisation scripts
import pickle

import pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent  # project root

with open(ROOT / 'data' / 'coauthor_data.pkl', 'wb') as f:
    pickle.dump({
        'chris_coauth_count': dict(chris_coauth_count),
        'pairwise_count': dict(pairwise_count),
        'author_pub_count': dict(author_pub_count),
        'CHRIS': CHRIS,
    }, f)
print("Saved.")
