"""PytSite Article Plugin API Functions
"""

__author__ = 'Oleksandr Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'

from typing import Optional as _Optional
from plugins import odm as _odm, content as _content
from . import _model


def _get_adjacent_entity(entity: _model.Article, same_author: bool, sort_order: int, **kwargs) \
        -> _Optional[_model.Article]:
    """Get content entity adjacent to `entity` by publish date
    """
    if not isinstance(entity, _model.Article):
        raise TypeError('{} is not an instance of {}'.format(entity.__class__, _model.Article))

    f = _content.find(entity.model, **kwargs).sort([('publish_time', sort_order)])

    if sort_order == _odm.I_ASC:
        f.gt('publish_time', entity.publish_time)
    else:
        f.lt('publish_time', entity.publish_time)

    if same_author:
        f.eq('author', entity.author)

    return f.first()


def get_previous_entity(entity: _model.Article, same_author: bool = False, **kwargs) -> _Optional[_model.Article]:
    return _get_adjacent_entity(entity, same_author, _odm.I_DESC, **kwargs)


def get_next_entity(entity: _model.Article, same_author: bool = False, **kwargs) -> _Optional[_model.Article]:
    return _get_adjacent_entity(entity, same_author, _odm.I_ASC, **kwargs)
