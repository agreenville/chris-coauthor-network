import docx, re, pickle, json, itertools, math
from collections import defaultdict
import networkx as nx
import community as community_louvain
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

import pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent  # project root


# ── Parse doc ────────────────────────────────────────────────────────────────
doc = docx.Document(ROOT / 'Chris_pubs.docx')
paragraphs = [p.text.strip() for p in doc.paragraphs]
SECTIONS = {
    'Books and journal theme issues': (2, 57),
    'Monographs': (57, 94),
    'Scientific articles': (148, 1045),
    'Chapters in books': (1045, 1330),
}

def join_paragraphs(paras):
    joined, current = [], ""
    for p in paras:
        if not p:
            if current: joined.append(current); current = ""
            continue
        if re.match(r'^[A-Z][a-zA-Záéíóúüñ\-\']+,\s+[A-Z]', p):
            if current: joined.append(current)
            current = p
        else:
            current = (current + " " + p).strip() if current else p
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
            r',\s*([A-Z](?:\.[A-Z])*\.(?:\s*[A-Z]\.)*(?:\s*[A-Z]-[A-Z]\.)?)',
            part):
            authors.append(f"{hit.group(1).strip()}, {hit.group(2).strip()}")
    return authors, m

def extract_title(ref, year_end):
    after = re.sub(r'^[\(\[]?\s*\d{4}\s*[\)\]]?\s*[a-z]?\s*[,\.]?\s*', '', ref[year_end:])
    m = re.search(r'\.\s+[A-Z][a-z]', after)
    return after[:m.start()].strip() if m else after[:140].strip()

CHRIS = "Dickman, C. R."
all_names_raw, raw_refs = set(), []
for sec, (s,e) in SECTIONS.items():
    for ref in join_paragraphs(paragraphs[s:e]):
        authors, ym = extract_authors(ref)
        if authors and any('Dickman' in a for a in authors):
            title = extract_title(ref, ym.end()) if ym else ""
            raw_refs.append({'authors': authors, 'title': title})
            all_names_raw.update(authors)

groups = defaultdict(list)
for name in all_names_raw:
    parts = name.split(',',1)
    last = parts[0].strip()
    fi = parts[1].strip()[0] if len(parts)>1 and parts[1].strip() else ''
    groups[(last,fi)].append(name)
canon_map = {}
for key, names in groups.items():
    canon = max(names, key=len)
    for n in names: canon_map[n] = canon
for n in list(canon_map):
    if 'Dickman' in n and 'C.' in n: canon_map[n] = CHRIS

refs = []
for r in raw_refs:
    norm = list(dict.fromkeys([canon_map.get(a,a) for a in r['authors']]))
    refs.append({'authors': norm, 'title': r['title']})

# ── Build graph ───────────────────────────────────────────────────────────────
G = nx.Graph()
pairwise = defaultdict(int)
author_pub_count = defaultdict(int)
chris_coauth_count = defaultdict(int)

for r in refs:
    auth = r['authors']
    for a in auth: author_pub_count[a] += 1
    if CHRIS not in auth: continue
    for other in auth:
        if other != CHRIS: chris_coauth_count[other] += 1
    for a,b in itertools.combinations(sorted(auth),2):
        pairwise[(a,b)] += 1

for (a,b),w in pairwise.items():
    G.add_edge(a,b,weight=w)

# ── Louvain with resolution tuned for 5-8 communities ────────────────────────
# Higher resolution → more communities; lower → fewer
best_partition = None
best_n = 999
for res in [0.3, 0.4, 0.5, 0.6, 0.7]:
    p = community_louvain.best_partition(G, weight='weight',
                                         resolution=res, random_state=42)
    n = len(set(p.values()))
    print(f"  resolution={res}: {n} communities")
    if abs(n - 6) < abs(best_n - 6):
        best_n = n
        best_partition = p

print(f"Selected: {best_n} communities")
partition_raw = best_partition

# ── Merge tiny communities into "Other" (keep top 7 by size) ─────────────────
MAX_COMMS = 7
comm_sizes = defaultdict(int)
for c in partition_raw.values(): comm_sizes[c] += 1
sorted_comms = [c for c,_ in sorted(comm_sizes.items(), key=lambda x: -x[1])]
keep = set(sorted_comms[:MAX_COMMS])
OTHER_ID = MAX_COMMS
remap = {c: i for i,c in enumerate(sorted_comms[:MAX_COMMS])}
partition = {n: remap.get(c, OTHER_ID) for n,c in partition_raw.items()}
n_communities = MAX_COMMS + (1 if any(v==OTHER_ID for v in partition.values()) else 0)
print(f"After merging small groups: {n_communities} final communities")

# ── TF-IDF theme labels ───────────────────────────────────────────────────────
STOP = {
    'a','an','the','and','or','of','in','on','to','with','by','for','from',
    'at','as','is','are','was','were','be','been','have','has','had',
    'its','their','this','that','these','those','such','not','but',
    'also','using','between','among','within','across','during',
    'effects','effect','role','impact','influence','change','changes',
    'patterns','pattern','study','studies','survey','note','evidence',
    'review','new','first','two','three','four','five','based','following',
    'associated','compared','related','responses','response','relationships',
    'relationship','used','data','analysis','results','management',
    'national','park','parks','north','south','east','west','central',
    # over-common ecology words
    'species','habitat','population','populations','ecology','ecological',
    'conservation','biodiversity','wildlife','fauna','flora','food','web',
}

comm_docs = defaultdict(list)
for r in refs:
    if not r['title']: continue
    votes = defaultdict(int)
    for a in r['authors']:
        if a in partition: votes[partition[a]] += 1
    if votes:
        comm_docs[max(votes, key=votes.get)].append(r['title'])

# Build one document per community for TF-IDF
comm_ids_present = sorted(comm_docs.keys())
corpus = [' '.join(comm_docs[c]) for c in comm_ids_present]

def tokenizer(text):
    return [w for w in re.findall(r'[a-z]{4,}', text.lower()) if w not in STOP]

tfidf = TfidfVectorizer(tokenizer=tokenizer, token_pattern=None, max_features=500)
try:
    X = tfidf.fit_transform(corpus)
    feature_names = tfidf.get_feature_names_out()
    community_themes = {}
    for i, c in enumerate(comm_ids_present):
        scores = X[i].toarray()[0]
        top_idx = scores.argsort()[::-1][:4]
        kws = [feature_names[j].capitalize() for j in top_idx if scores[j] > 0]
        community_themes[c] = ', '.join(kws[:3]) if kws else f'Group {c+1}'
except Exception as ex:
    print(f"TF-IDF failed: {ex}; falling back to frequency")
    community_themes = {c: f'Group {c+1}' for c in range(n_communities)}

# Name the "Other" group
if OTHER_ID < n_communities:
    community_themes[OTHER_ID] = 'Other collaborators'

print("\nFinal community themes:")
for c in range(n_communities):
    size = sum(1 for v in partition.values() if v == c)
    print(f"  {c}: [{size:3d} authors] {community_themes.get(c,'?')}")

# ── Community-aware layout ────────────────────────────────────────────────────
community_groups = defaultdict(list)
for node, c in partition.items(): community_groups[c].append(node)

centroid_radius = 3.5
centroids = {}
core_comms = [c for c in range(n_communities) if c != OTHER_ID]
for i, c in enumerate(core_comms):
    angle = 2*math.pi * i / len(core_comms)
    centroids[c] = np.array([centroid_radius*math.cos(angle),
                              centroid_radius*math.sin(angle)])
centroids[OTHER_ID] = np.array([0.0, 0.0])  # Other in centre

rng = np.random.default_rng(42)
init_pos = {}
for c, members in community_groups.items():
    cx, cy = centroids[c]
    for i, node in enumerate(members):
        angle = 2*math.pi * i / max(len(members), 1)
        r = 0.5 + rng.random()*0.8
        init_pos[node] = np.array([cx + r*math.cos(angle), cy + r*math.sin(angle)])

Glayout = G.copy()
for u,v,d in Glayout.edges(data=True):
    cu, cv = partition.get(u,-1), partition.get(v,-1)
    d['lw'] = d['weight'] * (4.0 if cu==cv else 0.3)

pos = nx.spring_layout(Glayout, pos=init_pos, weight='lw',
                        k=0.35, iterations=100, seed=42)

all_xy = np.array(list(pos.values()))
span = max(all_xy[:,0].max()-all_xy[:,0].min(),
           all_xy[:,1].max()-all_xy[:,1].min())
SCALE = 1600 / span if span > 0 else 1600

layout_positions = {n: (float(v[0]*SCALE), float(-v[1]*SCALE))
                    for n,v in pos.items()}

# ── Save ─────────────────────────────────────────────────────────────────────
with open(ROOT / 'data' / 'coauthor_data.pkl','rb') as f:
    base = pickle.load(f)

save = {**base,
        'partition': partition,
        'community_themes': community_themes,
        'layout_positions': layout_positions,
        'n_communities': n_communities,
        'OTHER_ID': OTHER_ID}
with open(ROOT / 'data' / 'community_data.pkl','wb') as f:
    pickle.dump(save, f)
print("\nSaved.")
