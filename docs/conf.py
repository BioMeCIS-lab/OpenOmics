#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# openomics documentation build configuration file, created by
# sphinx-quickstart on Fri Jun  9 13:47:02 2017.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

# If extensions (or modules to document with autodoc) are in another
# directory, add these directories to sys.path here. If the directory is
# relative to the documentation root, use os.path.abspath to make it
# absolute, like shown here.
#
import os
import sys

sys.path.insert(0, os.path.abspath('..'))

import openomics

# If your documentation needs a minimal Sphinx version, state it here.
#
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    'sphinx.ext.autodoc',
    # 'sphinx.ext.autosummary',
    'sphinx_autodoc_typehints',
    'sphinx.ext.linkcode',
    'sphinx.ext.napoleon',
    'myst_parser',

    # User Usability
    'sphinx_copybutton',
    'sphinx_inline_tabs',

    'sphinx.ext.coverage',
    'sphinx.ext.intersphinx',
    "sphinx.ext.viewcode",
    'sphinx_automodapi.automodapi',
    # 'sphinx_automodapi.smart_resolver',
    'sphinx.ext.graphviz',
    'sphinx.ext.inheritance_diagram',
]

autosummary_generate = False
autosummary_imported_members = True
napoleon_google_docstring = True
napoleon_use_param = True
napoleon_use_ivar = True
numpydoc_show_class_members = False

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']
exclude_patterns = ['_build', '_templates']

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
source_suffix = {
    '.rst': 'restructuredtext',
    '.txt': 'markdown',
    '.md': 'markdown',
}

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'OpenOmics'
copyright = "2019, Nhat Tran"
author = "Jonny Tran"

# The version info for the project you're documenting, acts as replacement
# for |version| and |release|, also used in various other places throughout
# the built documents.
#
# The short X.Y version.
version = openomics.__version__
# The full version, including alpha/beta/rc tags.
release = openomics.__version__

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = None

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This patterns also effect to html_static_path and html_extra_path
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# If true, `todo` and `todoList` produce output, else they produce nothing.
# todo_include_todos = True

# -- Options for Markdown files ----------------------------------------------

myst_enable_extensions = ["colon_fence", "deflist"]
myst_heading_anchors = 3

# -- Options for HTML output -------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'furo'

# Theme options are theme-specific and customize the look and feel of a
# theme further.  For a list of options available for each theme, see the
# documentation.

html_theme_options = {
    "sidebar_hide_name": False,
    "light_css_variables": {
        # "color-brand-primary": "#ff5c84",
        # "color-brand-content": "#ff5c84",
        "color-admonition-background": "#33cccc",
    },
}

html_logo = "../openomics_web/assets/openomics_logo.png"
html_favicon = '_static/favicon.png'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']
graphviz_dot = "/usr/bin/dot"

# -- Options for HTMLHelp output ---------------------------------------

# Output file base name for HTML help builder.
htmlhelp_basename = 'openomicsdoc'


# -- Options for manual page output ------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    (master_doc, 'openomics',
     u'OpenOmics Documentation',
     [author], 1)
]


def linkcode_resolve(domain, info):
    if domain != 'py':
        return None
    if not info['module']:
        return None
    filename = info['module'].replace('.', '/')
    return "https://github.com/BioMeCIS-Lab/OpenOmics/%s.py" % filename
