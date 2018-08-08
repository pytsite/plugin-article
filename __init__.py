"""PytSite Article Plugin
"""
__author__ = 'Oleksandr Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'

# Public API
from . import _model as model
from ._api import get_previous_entity, get_next_entity
from ._model import Article


def plugin_load():
    from pytsite import lang
    from plugins import permissions

    lang.register_package(__name__)
    permissions.define_group('article', 'article@articles')
