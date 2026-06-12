# PPT Build Directory

This directory keeps the reproducible source and selected deliverable for the
MZM group-meeting deck.

## Keep

| Path | Reason |
|------|--------|
| `build.py` | Deck generation script. Uses paths relative to this directory. |
| `template.pptx` | Source template required by `build.py`. |
| `formulas.json` | Formula source list. |
| `math/*.tex` | Formula render sources. |
| `math/*.png` | Formula images consumed directly by `build.py`. Keep unless a formula render script is added. |
| `math/manifest.json` | Formula dimensions used by `build.py`. |
| `inspect_template.txt` | Template inspection notes. |
| `output/*.pptx` | Final generated deck artifact worth keeping with docs. |

## Do Not Keep

| Path | Reason |
|------|--------|
| `qa/` | Rendered PDFs, page PNGs, and contact sheets; reproducible QA cache. |
| `.DS_Store` | macOS metadata. |
| `*.aux`, `*.log`, `*.out`, `*.pdf` | LaTeX/render temporary outputs. |

The repository `.gitignore` should ignore only the cache/temp files above, not
the whole `docs/ppt_build/` directory.
