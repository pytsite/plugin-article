"""PytSite Article Plugin Events Handlers
"""
__author__ = 'Oleksandr Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'

from plugins import content as _content, auth as _auth, comments as _comments


def on_content_view(entity: _content.ContentWithURL):
    if entity.has_field('comments_count') and entity.has_field('route_alias') and entity.route_alias:
        # Update entity's comments count
        try:
            _auth.switch_user_to_system()
            cnt = _comments.get_all_comments_count(entity.route_alias.alias)
            entity.f_set('comments_count', cnt).save(fast=True)
            return cnt
        finally:
            _auth.restore_user()
