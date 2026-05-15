# Chris Dickman Co-authorship Network

🔗 **[View the interactive network](https://agreenville.github.io/chris-coauthor-network/chris_coauthor_network.html)**

An interactive visualisation of co-authorship patterns across Chris Dickman's publication record, built from ~643 publications spanning his career at the University of Sydney.

## Overview

The network maps 1,059 unique co-authors connected by shared publications. Authors are grouped into six research communities detected by Louvain community detection and labelled by keyword analysis:

| Theme | Authors |
|-------|---------|
| Dasyurids & marsupials | 116 |
| Arid zone ecology | 129 |
| Predators & invasives | 310 |
| Threatened species & conservation | 207 |
| Plant ecology | 159 |
| Other | 138 |

## Outputs

| File | Description |
|------|-------------|
| `chris_coauthor_network.html` | Interactive network (open in any browser) |
| `chris_coauthor_network.png` | Static network — authors with ≥8 co-authored papers |
| `chris_coauthor_authors.csv` | Full author list with paper counts and theme |

## Interactive features

- **? Help guide** — click `? Help` in the toolbar for a step-by-step guided tour of all features
- **Theme isolation** — click a theme in the legend to focus on that community; click again to deselect and show all authors
- **Theme spacing / Node spacing** sliders — adjust layout density between and within clusters
- **Min papers filter** — show only authors above a co-authorship threshold with Chris
- **Co-author links toggle** — show/hide author-to-author edges (weighted by shared publications)
- **Move themes** mode — drag entire research communities to rearrange the layout
- **Search** — find any author by name; selecting a result zooms to and highlights that node
- **Download PNG** — export the current view as an image
- **Hover tooltips** — hover any node to see co-authorship details (papers with Chris, total publications, research theme); hover any edge to see the shared paper count
- Mobile-friendly (portrait and landscape)

Edge thickness and opacity both scale with the number of co-authored papers.

## Scripts

All scripts are in `scripts/` and should be run in order:

```bash
# 1. Parse publications and build co-authorship counts
python scripts/build_network.py

# 2. Assign theme labels and compute spring layout
python scripts/assign_themes.py

# 3. Generate interactive HTML
python scripts/make_community_html.py

# 4. (Optional) Generate static PNG
python scripts/make_png.py
```

`scripts/detect_communities.py` is an **alternative** to `assign_themes.py` — it
uses Louvain community detection + TF-IDF to discover themes automatically,
rather than the manual keyword-based themes in `assign_themes.py`. Both scripts
write to `data/community_data.pkl`, so run only one of them. The published
network uses `assign_themes.py` for stable, interpretable theme names.

### Dependencies

```
python-docx
networkx
python-louvain (community)
scikit-learn
matplotlib
numpy
```

Install with:
```bash
pip install python-docx networkx python-louvain scikit-learn matplotlib numpy
```

## Data

Intermediate data is stored in `data/`:
- `coauthor_data.pkl` — raw co-authorship counts
- `community_data.pkl` — community assignments, theme labels, and spring layout positions

## Colour palette

Wong (2011) colorblind-safe palette:
`#E69F00, #F0E442, #D55E00, #56B4E9, #009E73, #888888`

## Notes

- `make_community_html.py` contains em-dash characters in comments — add `# -*- coding: utf-8 -*-` at the top if running on Windows and encountering a SyntaxError.
- The source publication list (`Chris_pubs.docx`) is not included in this repository.
