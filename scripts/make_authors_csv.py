"""
make_authors_csv.py
Generates chris_coauthor_authors.csv from community_data.pkl:
one row per co-author with papers_with_chris, total_papers, and theme.

Run from any location:
    python scripts/make_authors_csv.py
"""
import csv
import pickle
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent  # project root
DATA_PKL = ROOT / 'data' / 'community_data.pkl'
OUT_CSV  = ROOT / 'chris_coauthor_authors.csv'

with open(DATA_PKL, 'rb') as f:
    data = pickle.load(f)

chris_coauth_count = data['chris_coauth_count']
author_pub_count   = data['author_pub_count']
partition          = data['partition']
community_themes   = dict(data['community_themes'])
OTHER_ID           = data['OTHER_ID']

# Match the theme-label override applied by make_community_html.py so the CSV
# stays consistent with the published HTML and the README themes table.
for k, v in list(community_themes.items()):
    if 'Vegetation' in v or ('plant' in v.lower() and 'Plant ecology' not in v):
        community_themes[k] = 'Plant ecology'

# Sort: papers_with_chris descending, then author name ascending
rows = sorted(
    chris_coauth_count.items(),
    key=lambda kv: (-kv[1], kv[0]),
)

with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
    w.writerow(['author', 'papers_with_chris', 'total_papers', 'theme'])
    for author, n_with_chris in rows:
        comm = partition.get(author, OTHER_ID)
        theme = community_themes.get(comm, 'Other')
        total = author_pub_count.get(author, n_with_chris)
        w.writerow([author, n_with_chris, total, theme])

print(f"Written: {OUT_CSV}")
print(f"  Rows: {len(rows):,}")
