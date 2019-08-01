"""PytSite Article Plugin Models
"""
__author__ = 'Oleksandr Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'

from random import random, shuffle
from pytsite import router, lang, events
from plugins import content, tag, auth, section, odm_ui, odm, widget, form, permissions


class Article(content.model.ContentWithURL):
    """Article Model
    """

    @property
    def starred(self) -> bool:
        """Is the article starred?
        """
        return self.f_get('starred')

    @property
    def section(self) -> section.model.Section:
        """Get article's section
        """
        return self.f_get('section')

    @classmethod
    def odm_auth_permissions_group(cls) -> str:
        """Hook
        """
        return 'article'

    @classmethod
    def on_register(cls, model: str):
        """Hook
        """
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

            # Counters
            for cnt_name in ('views', 'comments', 'likes', 'bookmarks'):
                f_name = cnt_name + '_count'
                if entity.has_field(f_name):
                    entity.f_set(f_name, int(random() * 1000))

        # Define 'set_starred' permission
        if odm.dispense(model).has_field('starred'):
            perm_name = 'article@set_starred.' + model
            perm_description = cls.resolve_lang_msg_id('content_perm_set_starred_' + model)
            permissions.define_permission(perm_name, perm_description, cls.odm_auth_permissions_group())

        events.listen('content@generate', on_content_generate)

    def _setup_fields(self, **kwargs):
        """Hook
        """
        super()._setup_fields(**kwargs)

        skip = kwargs.get('skip', [])

        # Images is required
        if self.has_field('images'):
            self.get_field('images').is_required = True

        # Section
        if 'section' not in skip:
            self.define_field(section.field.Section('section', is_required=True))

        # Starred
        if 'starred' not in skip:
            self.define_field(odm.field.Bool('starred'))

    def _setup_indexes(self):
        """Hook
        """
        super()._setup_indexes()

        for f in 'section', 'starred':
            if self.has_field(f):
                self.define_index([(f, odm.I_ASC)])

    def odm_ui_browser_setup(self, browser: odm_ui.Browser):
        """Hook
        """
        super().odm_ui_browser_setup(browser)

        # Section
        if self.has_field('section'):
            browser.insert_data_field('section', 'article@section')

        # Starred
        if self.has_field('starred') and auth.get_current_user().has_permission('article@set_starred.' + browser.model):
            browser.insert_data_field('starred', 'article@starred')

    def odm_ui_browser_row(self) -> dict:
        """Hook
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
        """Hook
        """
        super().odm_ui_m_form_setup_widgets(frm)

        # Starred
        if self.has_field('starred') and auth.get_current_user().has_permission('article@set_starred.' + self.model):
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

    def content_alter_route_alias_str(self, orig_str: str) -> str:
        """Hook
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
        """Hook
        """
        if self.has_field('section') and self.section:
            breadcrumb.append_item(self.section.title, router.rule_url('content@index', {
                'model': self.model,
                'term_field': 'section',
                'term_alias': self.section.alias,
            }))

        if self.has_field('title'):
            breadcrumb.append_item(self.title)

    def as_jsonable(self, **kwargs):
        """Get JSONable representation of the entity
        """
        r = super().as_jsonable(**kwargs)

        if self.has_field('starred'):
            r['starred'] = self.starred
        if self.has_field('section'):
            r['section'] = self.section.as_jsonable() if self.section else None

        return r
