# CLAUDE.md

Project context for future Claude sessions working in this folder.

## What this project is

An interactive co-authorship network visualisation of Chris Dickman's (Professor
of Terrestrial Ecology, University of Sydney) publication record — built from
~643 publications, mapping 1,059 unique co-authors across his career.

**This project was created for a celebratory forum and festschrift honouring
Chris Dickman's contributions to ecology.** It isn't a generic bibliometrics
exercise — the network, the website, and the printed leaflet in `Poster/` were
all produced as a tribute piece for that event. The leaflet was displayed at a
stand with laptops set up so attendees could scan a QR code, search for their
own name, and see their place in Chris's collaboration network. Keep this
celebratory, personal framing in mind for any text, captions, or copy added to
this project — it should read as a tribute, not a dry analysis.

Built and maintained by Aaron C. Greenville (School of Life and Environmental
Sciences, USYD), who also appears in the network as a top co-author.

## Live deliverable

- Live page: https://agreenville.github.io/chris-coauthor-network/chris_coauthor_network.html
- Repo: https://github.com/agreenville/chris-coauthor-network
- Hosted via GitHub Pages, deployed from the `main` branch root.

## File structure

| Path | Purpose |
|---|---|
| `chris_coauthor_network.html` | The deliverable — interactive vis.js network (~490 KB) |
| `chris_coauthor_authors.csv` | 1,059 authors with papers_with_chris, total_papers, theme |
| `chris_coauthor_network.png` | Static export, authors with ≥8 co-authored papers |
| `Poster/` | A4 print leaflet (docx/html/pdf source) + QR code + logo, made for the festschrift stand |
| `_Archive/` | Superseded PNG exports — reference only, not part of the deliverable |
| `scripts/` | Python pipeline that generates everything above (see below) |
| `data/coauthor_data.pkl` | Raw co-authorship counts (output of `build_network.py`) |
| `data/community_data.pkl` | Theme assignments + spring layout (output of `assign_themes.py`) |
| `Chris_pubs.docx` | Source publication list (~643 refs). Gitignored — not in the public repo. A fresh user must supply their own copy. |
| `Chris Dickman CV-2026.docx` | Chris's CV — background/bio source, also gitignored (`*.docx` pattern) |

## Pipeline — run in this order

```bash
python scripts/build_network.py        # 1. parse docx -> coauthor_data.pkl
python scripts/assign_themes.py        # 2. keyword themes + spring layout -> community_data.pkl
python scripts/make_community_html.py  # 3. inject data into the live HTML
python scripts/make_authors_csv.py     # 4. regenerate the author CSV
python scripts/make_png.py             # 5. optional static PNG
```

`scripts/detect_communities.py` is an **alternative** to `assign_themes.py`
(Louvain + TF-IDF auto-detected themes vs. the manual keyword approach). Both
write `data/community_data.pkl` — run only one. The published network uses
`assign_themes.py` for stable, interpretable theme names.

Dependencies: `python-docx networkx python-louvain scikit-learn matplotlib numpy`
(install with `pip install python-docx networkx python-louvain scikit-learn matplotlib numpy`)

## Key facts

- 643 publications · 1,059 unique co-authors · 6 research themes
- Top co-authors: Wardle (57), Greenville (52), Crowther (47), Newsome (46)
- Six themes: Dasyurids & marsupials (116), Arid zone ecology (129), Predators &
  invasives (310), Threatened species & conservation (207), Plant ecology (159),
  Other (138)
- Wong (2011) colourblind-safe palette: `#E69F00 #F0E442 #D55E00 #56B4E9 #009E73 #888888`
- HTML uses vis.js 4.21.0 (cdnjs, with SRI hashes). Physics runs once on load,
  then freezes; all later node movement writes x/y directly via `nodesDS.update()`.

## Working in this environment — gotchas that have bitten before

- **This is a OneDrive-synced folder.** Claude's `Edit`/`Write` tools are
  blocked here ("resolves to a protected location"). Make all edits via the
  `mcp__workspace__bash` sandbox instead (heredocs, or Python read/replace/write).
  Deleting files needs `mcp__cowork__allow_cowork_file_delete` first.
- **Never hand-edit `chris_coauthor_network.html` with a string-replace tool
  that has a size limit** — it has silently truncated the file (~490 KB) at
  least 4 times in past sessions, leaving it not ending in `</html>` and
  rendering blank. Always edit via Python `str.replace()` in bash and verify
  `content.endswith('</html>')` afterward. `make_community_html.py`'s
  template-injection approach (replace only the 6 JS data constants) exists
  specifically to avoid hand-editing this file — don't revert it to
  string-concatenation.
- **Don't run git commands from the sandbox while the user might have this
  repo open in PowerShell at the same time.** OneDrive syncing `.git` under
  concurrent access has corrupted `.git/index` more than once ("index file
  corrupt"). Prefer `find`/`ls` for local file checks, and `WebFetch` of
  `https://github.com/<user>/<repo>/tree/main/<path>` to check remote state
  (`github.com` is allowlisted from the sandbox; `api.github.com` is not, so
  the sandbox cannot push — the user pushes from PowerShell or GitHub Desktop).
  If `.git/HEAD.lock` or index corruption does occur, the user needs to run
  `Remove-Item .git\\HEAD.lock -Force` or `Remove-Item .git\\index -Force; git reset`
  themselves from PowerShell.
- **User is on Windows/PowerShell** — never chain shell commands with `&&`;
  use separate lines or `;`.

## Status as of 2026-06-21

- `Poster/` and `_Archive/` are new and untracked in git — not yet committed.
- `chris_coauthor_authors.csv` and `chris_coauthor_network.png` have local
  modifications not yet committed.
