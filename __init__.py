"""PytSite Article Plugin
"""
__author__ = 'Alexander Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'

from pytsite import plugman as _plugman

# Public API
if _plugman.is_installed(__name__):
    from . import _model as model


def plugin_load():
    from pytsite import lang

    lang.register_package(__name__)
