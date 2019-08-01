"""PytSite Article Plugin
"""
__author__ = 'Oleksandr Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'

# Public API
from ._model import Article


def plugin_load():
    from plugins import permissions

    permissions.define_group('article', 'article@articles')
