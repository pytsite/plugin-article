"""PytSite Article Plugin Models
"""
__author__ = 'Oleksandr Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'

from random import random as _random, shuffle as _shuffle
from typing import Tuple as _Tuple
from pytsite import validation as _validation, router as _router, lang as _lang, events as _events
from plugins import content as _content, comments as _comments, taxonomy as _taxonomy, tag as _tag, auth as _auth, \
    section as _section, odm_ui as _odm_ui, odm as _odm, widget as _widget, form as _form, permissions as _permissions


class Article(_content.model.ContentWithURL):
    """Article Model
    """

    @classmethod
    def on_register(cls, model: str):
        super().on_register(model)

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

        _events.listen('content@generate', on_content_generate)

    def _setup_fields(self):
        """Hook.
        """
        super()._setup_fields()

        self.get_field('images').required = True
        self.get_field('body').required = True

        self.define_field(_tag.field.Tags('tags'))
        self.define_field(_section.field.Section('section', required=True))
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

        for f in 'section', 'starred', 'views_count', 'comments_count':
            if self.has_field(f):
                self.define_index([(f, _odm.I_ASC)])

    @property
    def tags(self) -> _Tuple[_tag.model.Tag]:
        return self.f_get('tags', sort_by='weight', sort_reverse=True)

    @classmethod
    def odm_auth_permissions_group(cls) -> str:
        return 'article'

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

        # Section
        if mock.has_field('section'):
            browser.insert_data_field('section', 'article@section')

        # Starred
        if mock.has_field('starred') and c_user.has_permission('article@set_starred.' + browser.model):
            browser.insert_data_field('starred', 'article@starred')

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
                starred = '<span class="label label-primary badge badge-primary">{}</span>'. \
                    format(_lang.t('article@word_yes'))
            else:
                starred = '&nbsp;'
            r.append(starred)

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
                weight=50,
                label=self.t('starred'),
                value=self.starred,
            ))

        # Section
        if self.has_field('section'):
            frm.add_widget(_section.widget.SectionSelect(
                uid='section',
                weight=60,
                label=self.t('section'),
                value=self.section,
                h_size='col-xs-12 col-12 col-sm-6',
                required=self.get_field('section').required,
            ))

        # Tags
        if self.has_field('tags'):
            frm.add_widget(_taxonomy.widget.TokensInput(
                uid='tags',
                weight=250,
                model='tag',
                label=self.t('tags'),
                value=self.tags,
                required=self.get_field('tags').required,
            ))

        # External links
        if self.has_field('ext_links'):
            frm.add_widget(_widget.input.StringList(
                uid='ext_links',
                weight=550,
                label=self.t('external_links'),
                add_btn_label=self.t('add_link'),
                value=self.ext_links,
                unique=True,
                required=self.get_field('ext_links').required,
            ))
            frm.add_rule('ext_links', _validation.rule.Url())

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

    def content_breadcrumb(self, breadcrumb: _widget.select.Breadcrumb):
        if self.has_field('section') and self.section:
            breadcrumb.append_item(self.section.title, _router.rule_url('content@index', {
                'model': self.model,
                'term_field': 'section',
                'term_alias': self.section.alias,
            }))

        if self.has_field('title'):
            breadcrumb.append_item(self.title)

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
