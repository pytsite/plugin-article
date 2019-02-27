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
    from plugins import permissions

    permissions.define_group('article', 'article@articles')


def plugin_load_wsgi():
    from plugins import content
    from . import _eh

    content.on_content_view(_eh.on_content_view)
