"""PytSite Article Plugin.
"""
from . import _model as model

__author__ = 'Alexander Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'


def _init():
    from pytsite import lang, assetman

    lang.register_package(__name__, alias='article')
    assetman.register_package(__name__, alias='article')


_init()
