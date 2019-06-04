"""PytSite Article Plugin Events Handlers
"""
__author__ = 'Oleksandr Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'

from plugins import content, auth, comments


def on_content_view(entity: content.ContentWithURL):
    if entity.has_field('comments_count') and entity.has_field('route_alias') and entity.route_alias:
        # Update entity's comments count
        try:
            auth.switch_user_to_system()
            cnt = comments.get_all_comments_count(entity.route_alias.alias)
            entity.f_set('comments_count', cnt).save(fast=True)
            return cnt
        finally:
            auth.restore_user()
