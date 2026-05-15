# -*- coding: utf-8 -*-
"""
make_community_html.py
Regenerates chris_coauthor_network.html by reading community_data.pkl,
building fresh JSON data constants, and injecting them into the existing
HTML file (used as a template).  The HTML template contains all UI code;
only the data constants and counts are replaced.

Run from any location:
    python scripts/make_community_html.py
"""
import pickle, json, re, pathlib

ROOT     = pathlib.Path(__file__).resolve().parent.parent  # project root
DATA_PKL = ROOT / 'data' / 'community_data.pkl'
TEMPLATE = ROOT / 'chris_coauthor_network.html'
OUT_HTML = ROOT / 'chris_coauthor_network.html'  # overwrites template in-place

# ── Load data ─────────────────────────────────────────────────────────────────
with open(DATA_PKL, 'rb') as f:
    data = pickle.load(f)

chris_coauth_count = data['chris_coauth_count']
pairwise_count     = data['pairwise_count']
author_pub_count   = data['author_pub_count']
partition          = data['partition']
community_themes   = data['community_themes']
layout_positions   = data['layout_positions']
n_communities      = data['n_communities']
OTHER_ID           = data['OTHER_ID']
CHRIS              = data['CHRIS']

# Theme label overrides
community_themes = dict(community_themes)
for k, v in list(community_themes.items()):
    if 'Vegetation' in v or ('plant' in v.lower() and 'Plant ecology' not in v):
        community_themes[k] = 'Plant ecology'

# ── Build node / edge / legend arrays ─────────────────────────────────────────
COMM_COLOURS = ['#E69F00', '#F0E442', '#D55E00', '#56B4E9', '#009E73', '#888888']
COMM_BORDERS = ['#a06800', '#a09800', '#903000', '#2070a0', '#006848', '#555555']

MAX_CHRIS       = max(chris_coauth_count.values())
total_coauthors = len(chris_coauth_count)
total_pubs      = author_pub_count.get(CHRIS, 0)

coauth_list = sorted(chris_coauth_count.items(), key=lambda x: -x[1])
name_to_id  = {CHRIS: 0}
nodes_data  = [{
    'id': 0, 'label': 'Chris Dickman', 'fullname': CHRIS,
    'chris_count': total_pubs, 'pub_count': total_pubs,
    'is_chris': True, 'community': -1,
    'x': layout_positions.get(CHRIS, (0, 0))[0],
    'y': layout_positions.get(CHRIS, (0, 0))[1],
}]
for idx, (author, count) in enumerate(coauth_list, 1):
    name_to_id[author] = idx
    comm = partition.get(author, OTHER_ID)
    x, y = layout_positions.get(author, (0, 0))
    nodes_data.append({
        'id': idx, 'label': author, 'fullname': author,
        'chris_count': count, 'pub_count': author_pub_count.get(author, 0),
        'is_chris': False, 'community': comm, 'x': x, 'y': y,
    })

edges_data, eid = [], 0
for author, count in chris_coauth_count.items():
    if author in name_to_id:
        edges_data.append({
            'id': eid, 'from': 0, 'to': name_to_id[author],
            'weight': count, 'is_chris_edge': True,
        })
        eid += 1
for (a, b), count in pairwise_count.items():
    if a == CHRIS or b == CHRIS:
        continue
    if a in name_to_id and b in name_to_id and count >= 2:
        edges_data.append({
            'id': eid, 'from': name_to_id[a], 'to': name_to_id[b],
            'weight': count, 'is_chris_edge': False,
        })
        eid += 1

legend_entries = []
for c in range(n_communities):
    size   = sum(1 for v in partition.values() if v == c)
    theme  = community_themes.get(c, f'Group {c + 1}')
    colour = COMM_COLOURS[c] if c < len(COMM_COLOURS) else '#aaa'
    legend_entries.append({'id': c, 'colour': colour, 'theme': theme, 'size': size})

nodes_js   = json.dumps(nodes_data,   separators=(',', ':'))
edges_js   = json.dumps(edges_data,   separators=(',', ':'))
legend_js  = json.dumps(legend_entries, separators=(',', ':'))
colours_js = json.dumps(COMM_COLOURS, separators=(',', ':'))
borders_js = json.dumps(COMM_BORDERS, separators=(',', ':'))

# ── Read HTML template ────────────────────────────────────────────────────────
with open(TEMPLATE, 'r', encoding='utf-8') as f:
    html = f.read()

# ── Replace data constants (line-by-line; each constant is one long line) ─────
lines = html.split('\n')
replaced = set()
for i, line in enumerate(lines):
    s = line.strip()
    if s.startswith('const ALL_NODES'):
        lines[i] = f'const ALL_NODES    = {nodes_js};'
        replaced.add('ALL_NODES')
    elif s.startswith('const ALL_EDGES'):
        lines[i] = f'const ALL_EDGES    = {edges_js};'
        replaced.add('ALL_EDGES')
    elif s.startswith('const LEGEND'):
        lines[i] = f'const LEGEND       = {legend_js};'
        replaced.add('LEGEND')
    elif s.startswith('const COMM_COLOURS'):
        lines[i] = f'const COMM_COLOURS = {colours_js};'
        replaced.add('COMM_COLOURS')
    elif s.startswith('const COMM_BORDERS'):
        lines[i] = f'const COMM_BORDERS = {borders_js};'
        replaced.add('COMM_BORDERS')
    elif s.startswith('const MAX_CHRIS'):
        lines[i] = f'const MAX_CHRIS    = {MAX_CHRIS};'
        replaced.add('MAX_CHRIS')

missing = {'ALL_NODES','ALL_EDGES','LEGEND','COMM_COLOURS','COMM_BORDERS','MAX_CHRIS'} - replaced
if missing:
    raise ValueError(f"Could not find constants to replace: {missing}")

html = '\n'.join(lines)

# ── Update subtitle (publication + co-author counts in header) ────────────────
html = re.sub(
    r'<div class="subtitle">\d[\d,]* publications &middot; \d[\d,]* co-authors &middot; coloured by research theme</div>',
    f'<div class="subtitle">{total_pubs} publications &middot; {total_coauthors} co-authors &middot; coloured by research theme</div>',
    html
)

# ── Update counts in help tour welcome step ───────────────────────────────────
html = re.sub(
    r"Chris Dickman's \d[\d,]* publications and [\d,]+ co-authors",
    f"Chris Dickman's {total_pubs} publications and {total_coauthors:,} co-authors",
    html
)

# ── Write output ──────────────────────────────────────────────────────────────
with open(OUT_HTML, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Written: {OUT_HTML}")
print(f"  Nodes : {len(nodes_data):,}  (incl. Chris)")
print(f"  Edges : {len(edges_data):,}")
print(f"  Pubs  : {total_pubs}")
print(f"  Co-authors: {total_coauthors:,}")
