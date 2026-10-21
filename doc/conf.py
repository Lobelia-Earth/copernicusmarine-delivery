# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import tomllib
from pathlib import Path

data = tomllib.loads((Path(__file__).parent.parent / "pyproject.toml").read_text())

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = data["project"]["name"]
copyright = "2026, Lobelia Earth"
author = data["project"]["authors"][0]["name"]
version = data["project"]["version"]
release = version

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx_copybutton",
    "sphinx_click",
    "sphinxcontrib.autodoc_pydantic",
]

# Show `Path` instead of `pathlib.Path` in types.
python_use_unqualified_type_names = True

# Pydantic models: a table of fields (with types and defaults) instead of the
# constructor signature, and none of the pydantic internals.
autodoc_pydantic_model_show_json = False
autodoc_pydantic_model_show_config_summary = False
autodoc_pydantic_model_show_validator_summary = False
autodoc_pydantic_model_show_validator_members = False
autodoc_pydantic_model_show_field_summary = False
autodoc_pydantic_model_hide_paramlist = True
autodoc_pydantic_model_members_order = "bysource"
autodoc_pydantic_field_list_validators = False
autodoc_pydantic_field_show_constraints = False

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
html_title = "Copernicus Marine Delivery documentation"
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

# -- Hidden CLI options ------------------------------------------------------
# sphinx-click skips hidden options but still documents their environment
# variable (e.g. the operators-only `--pushing-entity-id`). Drop it from the docs.
from copernicusmarine_delivery.command_line_interface import cli  # noqa: E402

for _command in cli.commands.values():
    for _param in _command.params:
        if getattr(_param, "hidden", False):
            _param.envvar = None
