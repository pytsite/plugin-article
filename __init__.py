"""PytSite Article Plugin
"""
__author__ = 'Alexander Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'


# Public API
from . import _model as model
from ._api import get_previous_entity, get_next_entity
from ._model import Article


def plugin_load():
    from pytsite import lang

    lang.register_package(__name__)
