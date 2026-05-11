import pickle
import networkx as nx
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

with open('/sessions/confident-loving-ritchie/mnt/outputs/coauthor_data.pkl', 'rb') as f:
    data = pickle.load(f)

chris_coauth_count = data['chris_coauth_count']
pairwise_count = data['pairwise_count']
author_pub_count = data['author_pub_count']
CHRIS = data['CHRIS']

# Static plot: top 50 co-authors (≥8 papers with Chris)
THRESHOLD = 8
top_coauthors = {a: c for a, c in chris_coauth_count.items() if c >= THRESHOLD}
print(f"Authors with ≥{THRESHOLD} papers with Chris: {len(top_coauthors)}")

G = nx.Graph()
G.add_node(CHRIS)
for author in top_coauthors:
    G.add_node(author)

# Chris edges
for author, count in top_coauthors.items():
    G.add_edge(CHRIS, author, weight=count, is_chris_edge=True)

# Co-author edges (only between nodes already in graph, ≥3 shared pubs)
for (a, b), count in pairwise_count.items():
    if a == CHRIS or b == CHRIS:
        continue
    if a in top_coauthors and b in top_coauthors and count >= 3:
        G.add_edge(a, b, weight=count, is_chris_edge=False)

print(f"Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()}")

# Layout: spring with Chris pinned at centre
pos = nx.spring_layout(G, seed=42, k=2.5, iterations=100,
                        weight='weight')
pos[CHRIS] = np.array([0.0, 0.0])

fig, ax = plt.subplots(figsize=(20, 18), facecolor='#1a1a2e')
ax.set_facecolor('#1a1a2e')

# Draw co-author edges (non-Chris)
coauth_edges = [(u, v) for u, v, d in G.edges(data=True) if not d.get('is_chris_edge')]
coauth_weights = [G[u][v]['weight'] for u, v in coauth_edges]
if coauth_edges:
    nx.draw_networkx_edges(G, pos, edgelist=coauth_edges,
                           width=[0.5 + w * 0.3 for w in coauth_weights],
                           edge_color='#2a4a6a', alpha=0.5, ax=ax)

# Draw Chris edges
chris_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get('is_chris_edge')]
chris_weights = [G[u][v]['weight'] for u, v in chris_edges]
max_w = max(chris_weights) if chris_weights else 1
nx.draw_networkx_edges(G, pos, edgelist=chris_edges,
                       width=[1 + (w / max_w) * 8 for w in chris_weights],
                       edge_color='#e94560', alpha=0.55, ax=ax)

# Node sizes & colours
node_list = list(G.nodes())
node_sizes = []
node_colors = []
for n in node_list:
    if n == CHRIS:
        node_sizes.append(3000)
        node_colors.append('#e94560')
    else:
        c = chris_coauth_count.get(n, 1)
        node_sizes.append(200 + (c / max_w) * 1200)
        node_colors.append('#53c0a8')

nx.draw_networkx_nodes(G, pos, nodelist=node_list,
                       node_size=node_sizes, node_color=node_colors,
                       alpha=0.92, ax=ax)

# Labels - short names
short_labels = {}
for n in node_list:
    if n == CHRIS:
        short_labels[n] = 'Chris\nDickman'
    else:
        parts = n.split(',')
        last = parts[0].strip()
        inits = parts[1].strip() if len(parts) > 1 else ''
        first_init = inits.split('.')[0].strip() if inits else ''
        short_labels[n] = f"{last}\n{first_init}."

# Font sizes proportional to count
font_sizes = {}
for n in node_list:
    if n == CHRIS:
        font_sizes[n] = 11
    else:
        c = chris_coauth_count.get(n, 1)
        font_sizes[n] = max(6, min(10, 6 + c * 0.08))

for node, (x, y) in pos.items():
    ax.text(x, y, short_labels[node],
            fontsize=font_sizes[node],
            ha='center', va='center',
            color='white',
            fontweight='bold' if node == CHRIS else 'normal',
            zorder=5)

# Title & legend
ax.set_title("Chris Dickman — Co-authorship Network\n"
             f"(co-authors with ≥{THRESHOLD} shared publications shown)",
             color='white', fontsize=16, fontweight='bold', pad=15)

patch1 = mpatches.Patch(color='#e94560', label='Chris Dickman')
patch2 = mpatches.Patch(color='#53c0a8', label='Co-author (node size ∝ shared papers)')
line1 = matplotlib.lines.Line2D([0], [0], color='#e94560', linewidth=3,
                                  label='Chris ↔ co-author (line width ∝ shared papers)')
line2 = matplotlib.lines.Line2D([0], [0], color='#2a4a6a', linewidth=1.5, alpha=0.7,
                                  label='Co-author ↔ co-author (≥3 shared papers)')
ax.legend(handles=[patch1, patch2, line1, line2],
          loc='lower right', facecolor='#16213e', edgecolor='#0f3460',
          labelcolor='white', fontsize=9)

ax.axis('off')
plt.tight_layout()

out_path = '/sessions/confident-loving-ritchie/mnt/outputs/chris_coauthor_network.png'
plt.savefig(out_path, dpi=180, bbox_inches='tight',
            facecolor='#1a1a2e', edgecolor='none')
print(f"PNG saved.")
plt.close()
