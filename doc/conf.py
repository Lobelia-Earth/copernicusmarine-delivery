# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import tomllib
from pathlib import Path

data = tomllib.loads((Path(__file__).parent.parent / "pyproject.toml").read_text())

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "Copernicus Marine Producers Toolbox"
copyright = "2026, Lobelia Earth"
author = "Lobelia Earth"
version = data["project"]["version"]
release = version

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "myst_parser",
    "sphinx_copybutton",
]

myst_enable_extensions = [
    "colon_fence",
    "deflist",
]
myst_heading_anchors = 3

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "__pycache__"]

pygments_style = "sphinx"
pygments_dark_style = "monokai"

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
html_title = "Copernicus Marine Producers Toolbox"
html_static_path = ["_static"]
html_favicon = "_static/favicon_cmems.ico"
html_css_files = ["css/custom.css"]

# -- Options for the furo theme ----------------------------------------------
# https://pradyunsg.me/furo/customisation/

html_logo = "_static/favicon_cmems.ico"

html_theme_options = {
    "light_css_variables": {"color-brand-primary": "#607fad"},
}

html_sidebars = {
    "**": [
        "sidebar/brand.html",
        "sidebar/search.html",
        "sidebar/scroll-start.html",
        "sidebar/navigation.html",
        "sidebar/scroll-end.html",
        "sidebar/github.html",
    ]
}
