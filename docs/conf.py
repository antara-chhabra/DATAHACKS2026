project   = "DataHacks 2026 — Polymarket Analytics"
author    = "Team TQT"
copyright = "2026, Team TQT"
release   = "1.0.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "myst_parser",
]

source_suffix = {".rst": "restructuredtext", ".md": "markdown"}
master_doc    = "index"
html_theme    = "sphinx_rtd_theme"
html_static_path = ["_static"]

myst_enable_extensions = ["colon_fence", "tasklist"]

