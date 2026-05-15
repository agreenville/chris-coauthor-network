import docx, re, pickle, json, itertools, math
from collections import defaultdict
import networkx as nx
import numpy as np

import pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent  # project root


# ── reload parsed refs ────────────────────────────────────────────────────────
doc = docx.Document(ROOT / 'Chris_pubs.docx')
paragraphs = [p.text.strip() for p in doc.paragraphs]
SECTIONS = {'Books and journal theme issues':(2,57),'Monographs':(57,94),
            'Scientific articles':(148,1045),'Chapters in books':(1045,1330)}

def join_paragraphs(paras):
    joined, current = [], ""
    for p in paras:
        if not p:
            if current: joined.append(current); current=""
            continue
        if re.match(r'^[A-Z][a-zA-Záéíóúüñ\-\']+,\s+[A-Z]', p):
            if current: joined.append(current)
            current = p
        else:
            current = (current+" "+p).strip() if current else p
    if current: joined.append(current)
    return joined

def extract_authors(ref):
    m = re.search(r'\s*[\(\[]?\s*(1[89]\d\d|20[012]\d)\s*[\)\]]?\s*[a-z]?\s*[,\.]', ref)
    if not m: return [], m
    block = ref[:m.start()].strip().replace(' & ',' and ').replace('& ',' and ')
    authors = []
    for part in re.split(r'\s+and\s+', block):
        part = part.strip().rstrip(',')
        for hit in re.finditer(
            r'([A-Z][a-zA-Záéíóúüñ\-\']+(?:\s+[a-z]+\s+[A-Z][a-zA-Záéíóúüñ\-\']+)?)'
            r',\s*([A-Z](?:\.[A-Z])*\.(?:\s*[A-Z]\.)*(?:\s*[A-Z]-[A-Z]\.)?)', part):
            authors.append(f"{hit.group(1).strip()}, {hit.group(2).strip()}")
    return authors, m

def extract_title(ref, year_end):
    after = re.sub(r'^[\(\[]?\s*\d{4}\s*[\)\]]?\s*[a-z]?\s*[,\.]?\s*','',ref[year_end:])
    m2 = re.search(r'\.\s+[A-Z][a-z]', after)
    return after[:m2.start()].strip() if m2 else after[:160].strip()

CHRIS = "Dickman, C. R."
all_names_raw, raw_refs = set(), []
for sec,(s,e) in SECTIONS.items():
    for ref in join_paragraphs(paragraphs[s:e]):
        authors, ym = extract_authors(ref)
        if authors and any('Dickman' in a for a in authors):
            title = extract_title(ref, ym.end()) if ym else ""
            raw_refs.append({'authors': authors, 'title': title})
            all_names_raw.update(authors)

groups = defaultdict(list)
for name in all_names_raw:
    parts = name.split(',',1); last = parts[0].strip()
    fi = parts[1].strip()[0] if len(parts)>1 and parts[1].strip() else ''
    groups[(last,fi)].append(name)
canon_map = {}
for key, names in groups.items():
    canon = max(names,key=len)
    for n in names: canon_map[n] = canon
for n in list(canon_map):
    if 'Dickman' in n and 'C.' in n: canon_map[n] = CHRIS

refs = []
for r in raw_refs:
    norm = list(dict.fromkeys([canon_map.get(a,a) for a in r['authors']]))
    refs.append({'authors': norm, 'title': r['title']})

# ── 6 manually defined themes with keyword sets ───────────────────────────────
THEMES = [
    {
        'name': 'Dasyurids & marsupials',
        'keywords': [
            'dasyur','marsupial','antechinus','dasyurid','wallaby','possum','bandicoot',
            'wombat','koala','quoll','phascogale','planigale','sminthopsis','macropod',
            'dunnart','kowari','numbat','bilby','mulgara','ningaui','parantechinus',
            'potoroo','bettong','perameles','isoodon','macrotis','thylacomys',
            'carnivorous marsupial','native mammal','native mammals','small mammal',
            'small mammals','peramelid','dasyuridae','burramys','cercartetus',
        ],
    },
    {
        'name': 'Arid zone ecology',
        'keywords': [
            'arid','desert','dryland','outback','semi-arid','rainfall','boom','bust',
            'spinifex','chenopod','mulga','gibber','sturt','simpson','channel country',
            'rainfall variability','irruptive','flood','drought','pulse reserve',
            'boom-bust','rodent','house mouse','long-term','population dynamics',
        ],
    },
    {
        'name': 'Predators & invasives',
        'keywords': [
            'feral cat','feral cats','predator','predation','predatory','fox','foxes',
            'dingo','dingoes','invasive','introduced','exotic','cane toad','rabbit',
            'rats','rat','mice','mouse','mesopredator','trophic cascade','predator-prey',
            'lethal control','baiting','1080','poison','culling','feral','pest',
            'killing','removal','reintroduc','rewild','apex predator',
        ],
    },
    {
        'name': 'Threatened species & conservation',
        'keywords': [
            'threatened','conservation','extinct','extinction','endangered','critically',
            'recovery','critical weight range','biodiversity','protected area',
            'reserve','national park','listing','EPBC','red list','IUCN',
            'habitat loss','fragmentation','decline','declines','declining','loss',
            'restoration','reintroduction','captive','sanctuary','fence','fenced',
            'monitoring','fire','wildfire','bushfire',
        ],
    },
    {
        'name': 'Vegetation & plant ecology',
        'keywords': [
            'plant','vegetation','grass','shrub','biomass','tree','woodland','grassland',
            'flora','botany','botanical','seed','seedling','browse','grazing','pastoral',
            'soil','nutrient','carbon','nitrogen','productivity','primary production',
            'remote sensing','satellite','ndvi','greenness','cover','canopy',
        ],
    },
]
OTHER_THEME = {'name': 'Other', 'keywords': []}

def score_title(title, keywords):
    tl = title.lower()
    return sum(1 for kw in keywords if kw in tl)

# For each author, score their shared papers with Chris against each theme
author_theme_scores = defaultdict(lambda: [0]*len(THEMES))
author_pub_count    = defaultdict(int)
chris_coauth_count  = defaultdict(int)
pairwise_count      = defaultdict(int)

for r in refs:
    auth = r['authors']
    title = r['title']
    for a in auth: author_pub_count[a] += 1
    if CHRIS not in auth: continue
    others = [a for a in auth if a != CHRIS]
    for o in others:
        chris_coauth_count[o] += 1
        scores = [score_title(title, THEMES[i]['keywords']) for i in range(len(THEMES))]
        for i,s in enumerate(scores):
            author_theme_scores[o][i] += s
    for a,b in itertools.combinations(sorted(auth),2):
        pairwise_count[(a,b)] += 1

# Assign each co-author to dominant theme; tie → theme 5 (Other)
partition = {}
for author, scores in author_theme_scores.items():
    best = max(range(len(THEMES)), key=lambda i: scores[i])
    partition[author] = best if scores[best] > 0 else len(THEMES)  # 5 = Other
partition[CHRIS] = -1  # Chris gets special treatment

n_communities = len(THEMES) + 1   # 5 themes + Other
OTHER_ID = len(THEMES)             # = 5
community_themes = {i: THEMES[i]['name'] for i in range(len(THEMES))}
community_themes[OTHER_ID] = 'Other'

print("Theme assignment:")
for c in range(n_communities):
    size = sum(1 for v in partition.values() if v == c)
    print(f"  {c}: [{size:4d}] {community_themes[c]}")

# ── build full graph ──────────────────────────────────────────────────────────
G = nx.Graph()
for (a,b),w in pairwise_count.items():
    G.add_edge(a,b,weight=w)

# ── community-aware layout ────────────────────────────────────────────────────
community_groups = defaultdict(list)
for node,c in partition.items():
    if node != CHRIS: community_groups[c].append(node)

centroid_radius = 3.8
core_comms = list(range(len(THEMES)))           # 0-4 in a circle
centroids = {}
for i,c in enumerate(core_comms):
    angle = 2*math.pi * i / len(core_comms)
    centroids[c] = np.array([centroid_radius*math.cos(angle),
                              centroid_radius*math.sin(angle)])
centroids[OTHER_ID] = np.array([0.0, 0.0])     # Other in centre
centroids_chris = np.array([0.0, 0.0])          # Chris also centre

rng = np.random.default_rng(42)
init_pos = {CHRIS: np.array([0.0, 0.0])}
for c,members in community_groups.items():
    cx,cy = centroids[c]
    for i,node in enumerate(members):
        angle = 2*math.pi*i/max(len(members),1)
        r = 0.5 + rng.random()*0.9
        init_pos[node] = np.array([cx+r*math.cos(angle), cy+r*math.sin(angle)])

Glayout = G.copy()
for u,v,d in Glayout.edges(data=True):
    cu,cv = partition.get(u,-1), partition.get(v,-1)
    d['lw'] = d['weight'] * (4.5 if cu==cv and cu>=0 else 0.25)

pos = nx.spring_layout(Glayout, pos=init_pos, weight='lw',
                        k=0.3, iterations=120, seed=42)

all_xy = np.array(list(pos.values()))
span = max(all_xy[:,0].max()-all_xy[:,0].min(), all_xy[:,1].max()-all_xy[:,1].min())
SCALE = 1700 / span if span > 0 else 1700
layout_positions = {n: (float(v[0]*SCALE), float(-v[1]*SCALE)) for n,v in pos.items()}

# ── save ──────────────────────────────────────────────────────────────────────
save = {
    'chris_coauth_count': dict(chris_coauth_count),
    'pairwise_count': dict(pairwise_count),
    'author_pub_count': dict(author_pub_count),
    'CHRIS': CHRIS,
    'partition': partition,
    'community_themes': community_themes,
    'layout_positions': layout_positions,
    'n_communities': n_communities,
    'OTHER_ID': OTHER_ID,
}
with open(ROOT / 'data' / 'community_data.pkl','wb') as f:
    pickle.dump(save, f)
print("Saved.")
