"""PytSite Article Plugin Models
"""
__author__ = 'Oleksandr Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'

from random import random, shuffle
from typing import Tuple
from pytsite import validation, router, lang, events
from plugins import content, comments, taxonomy, tag, auth, section, odm_ui, odm, widget, form, permissions


class Article(content.model.ContentWithURL):
    """Article Model
    """

    @classmethod
    def on_register(cls, model: str):
        super().on_register(model)

        def on_content_generate(entity: content.model.Content):
            # Section
            if entity.has_field('section') and entity.has_field('language'):
                sections = list(section.get(entity.language))
                if not len(sections):
                    raise RuntimeError('No sections found')

                shuffle(sections)
                entity.f_set('section', sections[0])

            # Tags
            if entity.has_field('tags') and entity.has_field('language'):
                # Generate tags
                tags = list(tag.get(5, entity.language))
                if tags:
                    shuffle(tags)
                    entity.f_set('tags', tags)

            if entity.has_field('views_count'):
                entity.f_set('views_count', int(random() * 1000))

            if entity.has_field('comments_count'):
                entity.f_set('comments_count', int(random() * 100))

        mock = odm.dispense(model)

        # Define 'set_starred' permission
        if mock.has_field('starred'):
            perm_name = 'article@set_starred.' + model
            perm_description = cls.resolve_lang_msg_id('content_perm_set_starred_' + model)
            permissions.define_permission(perm_name, perm_description, cls.odm_auth_permissions_group())

        events.listen('content@generate', on_content_generate)

    def _setup_fields(self):
        """Hook.
        """
        super()._setup_fields()

        self.get_field('images').is_required = True
        self.get_field('body').is_required = True

        self.define_field(tag.field.Tags('tags'))
        self.define_field(section.field.Section('section', is_required=True))
        self.define_field(odm.field.Bool('starred'))
        self.define_field(odm.field.Integer('views_count'))
        self.define_field(odm.field.Integer('comments_count'))
        self.define_field(odm.field.UniqueStringList('ext_links'))

        for lng in lang.langs():
            self.define_field(odm.field.Ref('localization_' + lng, model=self.model))

    def _setup_indexes(self):
        """Hook.
        """
        super()._setup_indexes()

        for f in 'section', 'starred', 'views_count', 'comments_count':
            if self.has_field(f):
                self.define_index([(f, odm.I_ASC)])

    @property
    def tags(self) -> Tuple[tag.model.Tag]:
        return self.f_get('tags', sort_by='weight', sort_reverse=True)

    @classmethod
    def odm_auth_permissions_group(cls) -> str:
        return 'article'

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
    def section(self) -> section.model.Section:
        return self.f_get('section')

    @property
    def ext_links(self) -> Tuple[str]:
        return self.f_get('ext_links')

    def _on_f_get(self, field_name: str, value, **kwargs):
        """Hook.
        """
        if field_name == 'tags' and kwargs.get('as_string'):
            return ','.join([t.title for t in self.f_get('tags')])
        else:
            return super()._on_f_get(field_name, value, **kwargs)

    def _on_after_save(self, first_save: bool = False, **kwargs):
        """Hook.
        """
        super()._on_after_save(first_save, **kwargs)

        if first_save:
            # Recalculate tags weights
            if self.has_field('tags'):
                for t in self.tags:
                    weight = 0
                    for model in content.get_models().keys():
                        try:
                            weight += content.find(model, language=self.language).inc('tags', [t]).count()
                        except odm.error.FieldNotDefined:
                            pass

                    try:
                        auth.switch_user_to_system()
                        t.f_set('weight', weight).save(fast=True)
                    finally:
                        auth.restore_user()

        # Updating localization entities references.
        # For each language except current one
        for lng in lang.langs(False):
            # Get localization ref for lng
            localization = self.f_get('localization_' + lng)

            # If localization is set
            if isinstance(localization, content.model.Content):
                # If localized entity hasn't reference to this entity, set it
                if localization.f_get('localization_' + self.language) != self:
                    localization.f_set('localization_' + self.language, self).save()

            # If localization is not set
            elif localization is None:
                # Clear references from localized entities
                f = content.find(self.model, language=lng).eq('localization_' + self.language, self)
                for referenced in f.get():
                    referenced.f_set('localization_' + self.language, None).save()

    def _on_after_delete(self, **kwargs):
        """Hook.
        """
        # Delete comments
        if self.has_field('comments_count') and self.comments_count and \
                self.has_field('route_alias') and self.route_alias:
            try:
                auth.switch_user_to_system()
                comments.delete_thread(self.route_alias.alias)
            except (NotImplementedError, comments.error.NoDriversRegistered):
                pass
            finally:
                auth.restore_user()

        # We call this AFTER because super's method deletes route alias which is needed above
        super()._on_after_delete()

    def odm_ui_browser_setup(self, browser: odm_ui.Browser):
        """Setup ODM UI browser hook.
        """
        super().odm_ui_browser_setup(browser)

        c_user = auth.get_current_user()

        # Section
        if self.has_field('section'):
            browser.insert_data_field('section', 'article@section')

        # Starred
        if self.has_field('starred') and c_user.has_permission('article@set_starred.' + browser.model):
            browser.insert_data_field('starred', 'article@starred')

    def odm_ui_browser_row(self) -> dict:
        """Get single UI browser row hook.
        """
        r = super().odm_ui_browser_row()

        # Section
        if self.has_field('section') and self.section:
            r['section'] = self.section.title

        # Starred
        if self.has_field('starred') and auth.get_current_user().has_permission('article@set_starred.' + self.model):
            if self.starred:
                starred = '<span class="label label-primary badge badge-primary">{}</span>'. \
                    format(lang.t('article@word_yes'))
            else:
                starred = '&nbsp;'
            r['starred'] = starred

        return r

    def odm_ui_m_form_setup_widgets(self, frm: form.Form):
        """Hook.
        """
        super().odm_ui_m_form_setup_widgets(frm)

        c_user = auth.get_current_user()

        # Starred
        if self.has_field('starred') and c_user.has_permission('article@set_starred.' + self.model):
            frm.add_widget(widget.select.Checkbox(
                uid='starred',
                weight=50,
                label=self.t('starred'),
                value=self.starred,
            ))

        # Section
        if self.has_field('section'):
            frm.add_widget(section.widget.SectionSelect(
                uid='section',
                weight=60,
                label=self.t('section'),
                value=self.section,
                h_size='col-xs-12 col-12 col-sm-6',
                required=self.get_field('section').is_required,
            ))

        # Tags
        if self.has_field('tags'):
            frm.add_widget(taxonomy.widget.TokensInput(
                uid='tags',
                weight=250,
                model='tag',
                label=self.t('tags'),
                value=self.tags,
                required=self.get_field('tags').is_required,
            ))

        # External links
        if self.has_field('ext_links'):
            frm.add_widget(widget.input.StringList(
                uid='ext_links',
                weight=550,
                label=self.t('external_links'),
                add_btn_label=self.t('add_link'),
                value=self.ext_links,
                required=self.get_field('ext_links').is_required,
            ))
            frm.add_rule('ext_links', validation.rule.Url())

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

    def content_breadcrumb(self, breadcrumb: widget.select.Breadcrumb):
        if self.has_field('section') and self.section:
            breadcrumb.append_item(self.section.title, router.rule_url('content@index', {
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
            r['tags'] = [t.as_jsonable() for t in self.tags]
        if self.has_field('ext_links'):
            r['ext_links'] = self.ext_links
        if self.has_field('status'):
            r['status'] = self.status
        if self.has_field('views_count'):
            r['views_count'] = self.views_count
        if self.has_field('comments_count'):
            r['comments_count'] = self.comments_count

        for lng in lang.langs():
            if self.has_field('localization_' + lng):
                ref = self.f_get('localization_' + lng)
                if ref:
                    r['localization_' + lng] = ref.as_jsonable(**kwargs)

        return r
