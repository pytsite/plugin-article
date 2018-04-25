"""PytSite Article Plugin Models
"""
__author__ = 'Alexander Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'

from datetime import datetime as _datetime
from random import random as _random, shuffle as _shuffle
from typing import Tuple as _Tuple
from pytsite import validation as _validation, router as _router, lang as _lang, util as _util, events as _events, \
    errors as _errors
from plugins import content as _content, comments as _comments, taxonomy as _taxonomy, tag as _tag, auth as _auth, \
    section as _section, odm_ui as _odm_ui, odm as _odm, widget as _widget, form as _form, permissions as _permissions


class Article(_content.model.ContentWithURL):
    """Article Model
    """

    @classmethod
    def on_register(cls, model: str):
        super().on_register(model)

        def on_section_pre_delete(section: _section.model.Section):
            f = _content.find(model, status='*', check_publish_time=False)
            if not f.mock.has_field('section'):
                return

            r_entity = f.eq('section', section).first()
            if r_entity:
                error_args = {
                    'section_title': section.title,
                    'entity_model': r_entity.model,
                    'entity_title': r_entity.f_get('title')
                }
                raise _errors.ForbidDeletion(_lang.t('article@section_used_by_entity', error_args))

        def on_tag_pre_delete(tag: _tag.model.Tag):
            f = _content.find(model, status='*', check_publish_time=False)
            if not f.mock.has_field('tags'):
                return

            r_entity = f.inc('tags', tag).first()
            if r_entity:
                error_args = {
                    'tag_title': tag.title,
                    'entity_model': r_entity.model,
                    'entity_title': r_entity.f_get('title')
                }
                raise _errors.ForbidDeletion(_lang.t('article@tag_used_by_entity', error_args))

        def on_content_generate(entity: _content.model.Content):
            # Section
            if entity.has_field('section') and entity.has_field('language'):
                sections = list(_section.get(entity.language))
                if not len(sections):
                    raise RuntimeError('No sections found')

                _shuffle(sections)
                entity.f_set('section', sections[0])

            # Tags
            if entity.has_field('tags') and entity.has_field('language'):
                # Generate tags
                tags = list(_tag.get(5, entity.language))
                if tags:
                    _shuffle(tags)
                    entity.f_set('tags', tags)

            if entity.has_field('views_count'):
                entity.f_set('views_count', int(_random() * 1000))

            if entity.has_field('comments_count'):
                entity.f_set('comments_count', int(_random() * 100))

        mock = _odm.dispense(model)

        # Define 'set_starred' permission
        if mock.has_field('starred'):
            perm_name = 'article@set_starred.' + model
            perm_description = cls.resolve_msg_id('content_perm_set_starred_' + model)
            _permissions.define_permission(perm_name, perm_description, cls.odm_auth_permissions_group())

        # Define 'set_publish_time' permission
        if mock.has_field('publish_time'):
            perm_name = 'article@set_publish_time.' + model
            perm_description = cls.resolve_msg_id('content_perm_set_publish_time_' + model)
            _permissions.define_permission(perm_name, perm_description, cls.odm_auth_permissions_group())

        _events.listen('section@pre_delete', on_section_pre_delete)
        _events.listen('tag@pre_delete', on_tag_pre_delete)
        _events.listen('content@generate', on_content_generate)

    def _setup_fields(self):
        """Hook.
        """
        super()._setup_fields()

        self.get_field('images').required = True
        self.get_field('body').required = True

        self.define_field(_odm.field.DateTime('publish_time', default=_datetime.now()))
        self.define_field(_odm.field.RefsUniqueList('tags', model='tag'))
        self.define_field(_odm.field.Ref('section', model='section', required=True))
        self.define_field(_odm.field.Bool('starred'))
        self.define_field(_odm.field.Integer('views_count'))
        self.define_field(_odm.field.Integer('comments_count'))
        self.define_field(_odm.field.StringList('ext_links', unique=True))

        for lng in _lang.langs():
            self.define_field(_odm.field.Ref('localization_' + lng, model=self.model))

    def _setup_indexes(self):
        """Hook.
        """
        super()._setup_indexes()

        for f in 'publish_time', 'section', 'starred', 'views_count', 'comments_count':
            if self.has_field(f):
                self.define_index([(f, _odm.I_ASC)])

    @property
    def tags(self) -> _Tuple[_tag.model.Tag]:
        return self.f_get('tags', sort_by='weight', sort_reverse=True)

    def odm_ui_m_form_url(self, args: dict = None) -> str:
        return _router.rule_url('content@modify', {
            'model': self.model,
            'eid': '0' if self.is_new else str(self.id),
            '__redirect': 'ENTITY_VIEW',
        })

    @property
    def views_count(self) -> int:
        return self.f_get('views_count')

    @property
    def comments_count(self) -> int:
        return self.f_get('comments_count')

    @property
    def publish_time(self) -> _datetime:
        return self.f_get('publish_time')

    @property
    def publish_date_time_pretty(self) -> str:
        return self.f_get('publish_time', fmt='pretty_date_time')

    @property
    def publish_date_pretty(self) -> str:
        return self.f_get('publish_time', fmt='pretty_date')

    @property
    def publish_time_ago(self) -> str:
        return self.f_get('publish_time', fmt='ago')

    @property
    def starred(self) -> bool:
        return self.f_get('starred')

    @property
    def section(self) -> _section.model.Section:
        return self.f_get('section')

    @property
    def ext_links(self) -> _Tuple[str]:
        return self.f_get('ext_links')

    def _on_f_get(self, field_name: str, value, **kwargs):
        """Hook.
        """
        if field_name == 'tags' and kwargs.get('as_string'):
            return ','.join([tag.title for tag in self.f_get('tags')])
        else:
            return super()._on_f_get(field_name, value, **kwargs)

    def _after_save(self, first_save: bool = False, **kwargs):
        """Hook.
        """
        super()._after_save(first_save, **kwargs)

        if first_save:
            # Recalculate tags weights
            if self.has_field('tags'):
                for tag in self.tags:
                    weight = 0
                    for model in _content.get_models().keys():
                        try:
                            weight += _content.find(model, language=self.language).inc('tags', [tag]).count()
                        except _odm.error.FieldNotDefined:
                            pass

                    try:
                        _auth.switch_user_to_system()
                        tag.f_set('weight', weight).save()
                    finally:
                        _auth.restore_user()

        # Updating localization entities references.
        # For each language except current one
        for lng in _lang.langs(False):
            # Get localization ref for lng
            localization = self.f_get('localization_' + lng)

            # If localization is set
            if isinstance(localization, _content.model.Content):
                # If localized entity hasn't reference to this entity, set it
                if localization.f_get('localization_' + self.language) != self:
                    localization.f_set('localization_' + self.language, self).save()

            # If localization is not set
            elif localization is None:
                # Clear references from localized entities
                f = _content.find(self.model, language=lng).eq('localization_' + self.language, self)
                for referenced in f.get():
                    referenced.f_set('localization_' + self.language, None).save()

    def _after_delete(self, **kwargs):
        """Hook.
        """
        # Delete comments
        if self.has_field('route_alias') and self.route_alias:
            try:
                _auth.switch_user_to_system()
                _comments.delete_thread(self.route_alias.alias)
            except (NotImplementedError, _comments.error.NoDriversRegistered):
                pass
            finally:
                _auth.restore_user()

        # We call this AFTER because super's method deletes route alias which is needed above
        super()._after_delete()

    @classmethod
    def odm_ui_browser_setup(cls, browser: _odm_ui.Browser):
        """Setup ODM UI browser hook.
        """
        super().odm_ui_browser_setup(browser)

        mock = _odm.dispense(browser.model)
        c_user = _auth.get_current_user()

        # Sort field
        if mock.has_field('publish_time'):
            browser.default_sort_field = 'publish_time'
            browser.default_sort_order = 'desc'

        # Section
        if mock.has_field('section'):
            browser.insert_data_field('section', 'article@section')

        # Starred
        if mock.has_field('starred') and c_user.has_permission('article@set_starred.' + browser.model):
            browser.insert_data_field('starred', 'article@starred')

        # Publish time
        if mock.has_field('publish_time'):
            browser.insert_data_field('publish_time', 'article@publish_time')

    def odm_ui_browser_row(self) -> list:
        """Get single UI browser row hook.
        """
        r = super().odm_ui_browser_row()

        c_user = _auth.get_current_user()

        # Section
        if self.has_field('section'):
            r.append(self.section.title if self.section else '&nbsp;')

        # Starred
        if self.has_field('starred') and c_user.has_permission('article@set_starred.' + self.model):
            if self.starred:
                starred = '<span class="label label-primary">{}</span>'.format(_lang.t('article@word_yes'))
            else:
                starred = '&nbsp;'
            r.append(starred)

        # Publish time
        if self.has_field('publish_time'):
            r.append(self.f_get('publish_time', fmt='%d.%m.%Y %H:%M'))

        return r

    def odm_ui_m_form_setup_widgets(self, frm: _form.Form):
        """Hook.
        """
        super().odm_ui_m_form_setup_widgets(frm)

        c_user = _auth.get_current_user()

        # Starred
        if self.has_field('starred') and c_user.has_permission('article@set_starred.' + self.model):
            frm.add_widget(_widget.select.Checkbox(
                uid='starred',
                weight=100,
                label=self.t('starred'),
                value=self.starred,
            ))

        # Section
        if self.has_field('section'):
            frm.add_widget(_section.widget.SectionSelect(
                uid='section',
                weight=150,
                label=self.t('section'),
                value=self.section,
                h_size='col-sm-6',
                required=self.get_field('section').required,
            ))

        # Tags
        if self.has_field('tags'):
            frm.add_widget(_taxonomy.widget.TokensInput(
                uid='tags',
                weight=450,
                model='tag',
                label=self.t('tags'),
                value=self.tags,
                required=self.get_field('tags').required,
            ))

        # External links
        if self.has_field('ext_links'):
            frm.add_widget(_widget.input.StringList(
                uid='ext_links',
                weight=1100,
                label=self.t('external_links'),
                add_btn_label=self.t('add_link'),
                value=self.ext_links,
                unique=True,
                required=self.get_field('ext_links').required,
            ))
            frm.add_rule('ext_links', _validation.rule.Url())

        # Publish time
        if self.has_field('publish_time') and c_user.has_permission('article@set_publish_time.' + self.model):
            frm.add_widget(_widget.select.DateTime(
                uid='publish_time',
                weight=1300,
                label=self.t('publish_time'),
                value=_datetime.now() if self.is_new else self.publish_time,
                h_size='col-sm-4 col-md-3 col-lg-2',
                required=True,
            ))

    def _alter_route_alias_str(self, orig_str: str) -> str:
        """Alter route alias string.
        """
        # Checking original string
        if not orig_str:
            # Route alias string generation is possible only if entity's title is not empty
            if self.title:
                orig_str = self.title
                if self.has_field('section') and self.section:
                    # If 'section' field exists and section is selected, use its alias
                    orig_str = '{}/{}'.format(self.section.alias, orig_str)
                else:
                    # Otherwise use model name
                    orig_str = '{}/{}'.format(self.model, orig_str)
            else:
                # Without entity's title we cannot construct route alias string
                raise RuntimeError('Cannot generate route alias because title is empty.')

        return orig_str

    def as_jsonable(self, **kwargs):
        r = super().as_jsonable(**kwargs)

        if self.has_field('starred'):
            r['starred'] = self.starred
        if self.has_field('section'):
            r['section'] = self.section.as_jsonable() if self.section else None
        if self.has_field('tags'):
            r['tags'] = [tag.as_jsonable() for tag in self.tags]
        if self.has_field('ext_links'):
            r['ext_links'] = self.ext_links
        if self.has_field('status'):
            r['status'] = self.status
        if self.has_field('publish_time'):
            r['publish_time'] = {
                'w3c': _util.w3c_datetime_str(self.publish_time),
                'pretty_date': self.publish_date_pretty,
                'pretty_date_time': self.publish_date_time_pretty,
                'ago': self.publish_time_ago,
            }
        if self.has_field('views_count'):
            r['views_count'] = self.views_count
        if self.has_field('comments_count'):
            r['comments_count'] = self.comments_count

        for lng in _lang.langs():
            if self.has_field('localization_' + lng):
                ref = self.f_get('localization_' + lng)
                if ref:
                    r['localization_' + lng] = ref.as_jsonable(**kwargs)

        return r
