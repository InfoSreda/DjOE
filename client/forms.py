from lxml import etree
from django import forms
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.core.context_processors import csrf
from django.contrib.auth.forms import AuthenticationForm
from djoe.client.widgets import *


class OpenERPAuthForm(AuthenticationForm):

    database = forms.CharField(label=_("Database"), max_length=30)

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        database = self.cleaned_data.get('database')

        if username and password:
            self.user_cache = authenticate(username=username,
                                           password=password,
                                           database=database,
                                           session=request.oe_session)
            if self.user_cache is None:
                raise forms.ValidationError(_("Please enter a correct username'\
                  'and password. Note that both fields are case-sensitive."))
        self.check_for_test_cookie()
        return self.cleaned_data

FIELD_WIDGET_MAP = {
    forms.NullBooleanField: OECheckboxInput,
    forms.DateField: DateFieldWidget,
    forms.DateTimeField: DateFieldWidget,
    }


ICON_MAP = {
    'go-forward': 'go-next-ltr',
    'execute': 'system-run',
    'jump-to-ltr': 'go-jump-ltr',
    'jump-to': 'go-jump-ltr',
    'go-back-rtl': 'go-previous-rtl',
    'dialog-close': 'window-close',
    'media-play': 'media-playback-start-ltr',
    'find': 'edit-find'
    }

def safe_eval(expr, globs=None, locs=None):
    if globs is None:
        globs = {}
    if locs is None:
        locs = {}
    try:
        res = eval(expr, globs, locs)
    except:
        # TODO: correct work with exception
        return None
    return res


class OpenERPBaseView(object):

    def __init__(self, model_class=None, view_id=None,
                 search_view_id=None, with_edit=False):
        self.model_class = model_class
        self.search_view_id = search_view_id
        self.with_edit = with_edit

        self.hidden_html = []
        self._cached_html = None
        oe_view = self.model_class.objects.oe_fields_view_get(view_id,
                                                              self.view_type)
        if self.model_class._openerp_only_name:
            self.model_class = self.model_class._openerp_session.get_model(
               self.model_class._openerp_model, all_oe_fields=oe_view['fields'])

        self.oe_model = model_class._openerp_model
        self.fields = oe_view['fields']
        self.arch = etree.fromstring(oe_view['arch'])
        self.view_id = view_id

    def remove_notview_model_fields(self):
        fields = set(self.fields)

        view_fields = []
        for f in self.model_class._meta.local_fields:
            if f.name in fields:
                view_fields.append(f)
        self.model_class._meta.local_fields = view_fields
        m2m_view_fields = []

        for f in self.model_class._meta.local_many_to_many:
            if f.name in fields:
                m2m_view_fields.append(f)
        self.model_class._meta.local_many_to_many = m2m_view_fields
    
        del self.model_class._meta._field_cache
        #if hasattr(o2m_model._meta, '_field_name_cache'):
        del self.model_class._meta._field_name_cache


    def get_width(self, field, colspan=None):
        return ''

    def get_top_html(self):
        return []

    def get_bottom_html(self):
        return []

    def _html_icon(self, icon):
        if icon.startswith('terp-'):
            icon = icon[5:]
        if icon.startswith('gtk-'):
            icon = icon[4:]
        icon = ICON_MAP.get(icon, icon)
        return ['<img src="/static/img/gtk-icons/%s.png"/>' % icon ]

    def _html_button(self, button):
        icon = button.attrib.get('icon')
        title = button.attrib.get('help', button.attrib.get('string', ''))
        html = ['<button class="form_button k-button ',
                ('special_%s' % button.attrib['special']) if 'special' \
                 in button.attrib else '',
                '" type="button" title="%s" style="%s">' \
                % (title, self.get_width(button))]
        if icon:
            html.extend(self._html_icon(icon))
        html.append('</button>')
        return html

    def _create_html(self, element):
        html = []
        for child in element.iterchildren():
            if isinstance(child, etree._Comment):
                continue
            child_html = getattr(self, '_html_%s' % child.tag)(child)
            html.extend(child_html)
        return html

    def get_html(self):
        if self._cached_html is None:
            html = self.get_top_html()
            html.extend(self._create_html(self.arch))
            if not self.hidden_html:
                return mark_safe(''.join(html))
            all_html = ['<div style="display:none;">']
            all_html.extend(self.hidden_html)
            all_html.append('</div>')
            all_html.extend(html)
            all_html.extend(self.get_bottom_html())
            self._cached_html = mark_safe(''.join(all_html))
        return self._cached_html

    def render(self):
        return {'view_html': self.get_html()}


class OpenERPTreeView(OpenERPBaseView):

    view_type = 'tree'
    template = 'djoe/client/tree_grid.html'

    def __init__(self, *args, **kwargs):
        super(OpenERPTreeView, self).__init__(*args, **kwargs)
        self.headers = []
        self.colors = None

    def get_url(self):
        if self.view_id and self.search_view_id:
            url = reverse('djoe_client:ajax_object_search_with_views',
                       args=(self.oe_model,
                             self.view_id,
                             self.search_view_id))
        else:
            url = reverse('djoe_client:ajax_object_search',
                       args=(self.oe_model,))
        if self.with_edit:
            url += '?_with_edit=true'
        return url

    def prepare_colors(self):
        tree_colors = tree_arch.attrib.get('colors', '')
        if tree_colors:
            all_color_variant = tree_colors.split(';')
            color_pair = ('%s:"%s"' % (s[1], s[0]) for s in \
                          (s.split(':') for s in all_color_variant))
            self.colors = '{%s}' % ', '.join(color_pair) 

    def get_color(self, row):
        color = 'black'
        if self.colors is not None:
            color_dict = safe_eval(self.colors, row.copy())
            if color_dict:
                return color_dict.get(True, 'black')
        return color

    def _html_field(self, field):
        if field.attrib.get('invisible'):
            return []
        field_name = field.attrib['name']
        field_title = field.attrib.get('string')
        if field_title is None:
            field_title = self.model_class._meta.get_field(field_name) \
                          .verbose_name
        html = ['<td>${ ', field_name, ' }</td>']
        self.headers.append({'field':field_name, 'title':field_title})
        return html

    def _html_button(self, button):
        html = ['<td>']
        html.extend(super(OpenERPTreeView, self)._html_button(button))
        html.append('</td>')
        self.headers.append({'field':None, 'title':''})
        return html

    def _create_html(self, element):
        self.headers = []
        html = ['<tr rowid="${ __id }" style="color:${ __color }">']
        if self.with_edit:
            html.extend([
                '<td nowrap>',
                '<a href="">',
                '<span class="k-icon k-edit"></span></a></td>'])
        html.extend(super(OpenERPTreeView, self)._create_html(element))
        if self.with_edit:
            html.extend(['<td><a href="">',
                     '<span class="k-icon k-delete"></span></a></td>'])
        html.append('</tr>')
        return html

    def render(self):
        self.get_html()
        rend = render_to_string(self.template, {'tree_view': self})
        return {'view_html': rend, 'dataUrl': self.get_url()}


class OpenERPBaseFormView(OpenERPBaseView):

    FIELD_MAP = {
        'char': forms.CharField,
        #'url'
        'email': forms.EmailField,
        'image': forms.FileField,
        'datetime': forms.DateTimeField,
        'float_time': forms.FloatField,
        'one2many': OEOneToManyField,
        'one2many_list': OEOneToManyField,
        'many2many': OEManyToManyField,
        'many2many_list': OEManyToManyField,
        'many2one': OEManyToOneField,
    }

    hidden_field_class = OEHiddenInput


    def __init__(self, data=None, instance=None, csrf_token=None,
                 initial=None,
                 *args, **kwargs):
        super(OpenERPBaseFormView, self).__init__(*args, **kwargs)
        form_class = self.get_form_class()
        if initial is None:
            self.initial = initial
        self.instance = instance
        self.form = form_class(data=data, instance=instance, initial=initial)
        for field in self.form.fields.values():
            self._field_prepare(field)
        self.default_col = 4
        self.col = self.default_col
        self.csrf_token = csrf_token

    def get_intial(self):
        return {}

    def is_valid(self):
        return self.form.is_valid()

    def save(self, **kwargs):
        return self.form.save(**kwargs)

    def check_invisible(self, attribs):
        invisible = attribs.get('invisible')
        if invisible is None:
            return False
        return invisible in ('1', 'True', 'true')

    @property
    def errors(self):
        return self.form.errors

    def make_field(self, field_type, attrs, **kwargs):
        is_hidden = self.check_invisible(attrs)

        if is_hidden:
            kwargs['widget'] = self.hidden_field_class()

        widget = attrs.get('widget')
        if widget:
            if widget == 'selection':
                if field_type in ('many2one', 'one2many'):
                    field_class = forms.ModelChoiceField
                    model = kwargs.pop('model')
                    kwargs['queryset'] = model.objects.all()
                else:
                    field_class = forms.ChoiceField
            else:
                field_class = self.FIELD_MAP[widget]
        else:
            field_class = self.FIELD_MAP[field_type]
        return field_class(**kwargs)

    def get_form_fields(self):
        return self.arch.xpath('//field')

    def get_form_class(self):
        form_fields = self.get_form_fields()
        field_dict = dict(( (f.attrib['name'], f) for f in form_fields))
        klass_meta = type('Meta', (), {'model': self.model_class,
                                       'fields': field_dict.keys()})
        attrs = {'Meta': klass_meta}
        self.o2m_fields = set(field_dict.keys())

        for field in self.model_class._meta.fields:
            if field.name in self.o2m_fields:
                self.o2m_fields.remove(field.name)
            else:
                continue
            attribs = field_dict[field.name].attrib
            if isinstance(field, models.ForeignKey):
                attrs[field.name] = self.make_field('many2one',
                                                    attribs,
                                                    model=field.rel.to,
                                                    label=field.verbose_name,
                                                    required=not(field.blank))
            elif 'widget' in attribs:
                attrs[field.name] = self.make_field(None,
                                                    attribs,
                                                    label=field.verbose_name,
                                                    required=not(field.blank))
                

        for field in self.model_class._meta.many_to_many:
            if field.name in self.o2m_fields:
                self.o2m_fields.remove(field.name)
            else:
                continue
            attrs[field.name] = self.make_field('many2many',
                                                field_dict[field.name].attrib,
                                                model=field.rel.to,
                                                label=field.verbose_name,
                                                required=not(field.blank))

        for field_name in self.o2m_fields:
            required = field_name in self.model_class._openerp_readonly_fields
            field = getattr(self.model_class, field_name)
            if hasattr(field, 'field'):
                model = field.field.rel.to
            else:
                model = field.related.model
            attrs[field_name] = self.make_field('one2many',
                                                field_dict[field_name].attrib,
                                                model=model,
                                                #label=field.verbose_name,
                                                required=required)
        klass_form = type('ItemForm', (forms.ModelForm,), attrs)
        return klass_form

    def _html_newline(self, new_line):
        return '<br/>'

    def _html_html(self, html):
        return ''

    def _field_prepare(self, field):
        if field.__class__ in FIELD_WIDGET_MAP:
            field.widget = FIELD_WIDGET_MAP[field.__class__]()

    def _html_field(self, field):
        field_name = field.attrib['name']
        form_field = self.form[field_name]

        if self.check_invisible(field.attrib):
            self.hidden_html.append(unicode(form_field))
            return []
        if not field.attrib.get('nolabel'):
            html = ['<label style="%s">' % self.get_width(field, 1),
                    field.attrib.get('string') or form_field.label, ':</label>']
        else:
            html = []
        html.extend(['<span class="form_field" style="%s">' % \
                     self.get_width(field), unicode(form_field), '</span>'])
        return html

    def _html_label(self, label):
        html = ['<span class="form_label" style="%s">' % self.get_width(label),
                label.attrib.get('string', ''), '</span>']
        return html

    def _html_separator(self, separator):
        orient = separator.attrib.get('orientation', 'horizontal')
        styles = ['height:%sem' % (1.2 * int(separator.attrib.get('rowspan', 1)))]
        if orient == 'horizontal':
            styles.append(self.get_width(separator))
        return ['<span class="separator_', orient,'" style="',
                ';'.join(styles), '">',
                separator.attrib.get('string','&nbsp;'), '</span>']

    def _html_group(self, group):
        states = group.attrib.get('states')
        if self.instance and states is not None:
            if not self.instance.state in \
                   [s.strip() for s in states.split(',')]:
                return []

        invisible = self.check_invisible(group)
        html = ['<div class="form_group" style="',
                self.get_width(group, float(group.attrib.get('colspan', 4))),
                ';display:none;' if invisible else '',
                '">']
        pre_col = self.col
        self.col = group.attrib.get('col', self.default_col)
        html.extend(self._create_html(group))
        self.col = pre_col
        html.append('</div>')
        return html

    def _html_newline(self, new_line):
        return '<br/>'


class OpenERPSearchView(OpenERPBaseFormView):

    view_type = 'search'
    template = 'djoe/client/search_view.html'

    form_root_tag = 'search'
    o2m_field_class = OEManyToOneField
    m2m_field_class = OEManyToOneField

    def _field_prepare(self, field):
        field.required = False
        if isinstance(field.widget, forms.SelectMultiple):
            field.widget = forms.Select()
        elif isinstance(field.widget, forms.Textarea):
            field.widget = forms.TextInput()
        else:
            super(OpenERPSearchView, self)._field_prepare(field)

    def _html_group(self, group):
        expand = group.attrib.get('expand', True)
        if expand in ('0', 'False'):
            expand = False
        icon = ['k-plus', 'k-minus'][int(expand)]
        html = ['<div class="group_treeview">',
                  '<div class="k-top k-bot">',
                   '<span class="k-icon ',  icon, '">',
                    '</span><span class="k-in">',
                        group.attrib.get('string', ''),
                    '</span></div><div class="k-group ',
                'expanded' if expand else '', 
                '"><div class="k-item">']
        html.extend(self._create_html(group))
                
        html.append('</div></div></div>')
        return html

    def _html_field(self, field):
        sup_field = super(OpenERPSearchView, self)._html_field(field)
        childs = self._create_html(field)
        html = ['<span class="search_field">']
        html.extend(sup_field)
        if childs:
            html.extend(childs)
        html.append('</span>')
        return html

    def _html_filter(self, filtr):
        html = super(OpenERPSearchView, self)._html_button(filtr)
        if 'string' in filtr.attrib:
            html.insert(-1, '<br/>%s' % filtr.attrib['string'])
        return html

    def render(self):
        rend = render_to_string(self.template, {'search_view': self})
        return {'search_view_html': rend}


class OpenERPFormView(OpenERPBaseFormView):

    view_type = 'form'
    form_root_tag = 'form'
    template = 'djoe/client/form_view.html'

    def get_url(self):
        object_id = self.instance and self.instance.pk or 0
        if self.view_id:
            url = reverse('djoe_client:object_edit_with_view',
                       args=(self.oe_model, object_id, self.view_id))
        else:
            url = reverse('djoe_client:object_edit',
                       args=(self.oe_model, object_id))
        return url

    def get_width(self, field, colspan=None):
        res = []
        if 'height' in field.attrib:
            res.append('min-height:%spx;display:inline-block' % field.attrib['height'])
        if 'width' in field.attrib:
            res.append('min-width:%spx;display:inline-block' % field.attrib['width'])
        nolabel = field.attrib.get('nolabel')
        if colspan is None:
            colspan = float(field.attrib.get('colspan', 1))
        if nolabel:
            colspan += 1
        if colspan > self.col:
            colspan = self.col
        res.append('width:%.2f%%' % (98 * (colspan/float(self.col))))
        return ';'.join(res)

    def _field_prepare(self, field):
        if field.required:
            field.widget.attrs['class'] = 'required_field'
        super(OpenERPFormView, self)._field_prepare(field)

    def _html_field(self, field):
        field_name = field.attrib['name']
        if field_name in self.model_class._openerp_readonly_fields \
               and not self.form.fields[field_name].required:
            self.form.fields[field_name].widget.attrs['disabled'] = True
        return super(OpenERPFormView, self)._html_field(field)

    def _html_separator(self, separator):
        orient = separator.attrib.get('orientation', 'horizontal')
        styles = ['height:%sem' % (1.2 * int(separator.attrib.get('rowspan', 1)))]
        styles.append(self.get_width(separator))
        return ['<span class="separator_', orient,'" style="',
                ';'.join(styles), '">',
                separator.attrib.get('string','&nbsp;'), '</span>']

    def _html_button(self, button):
        states = button.attrib.get('states')
        if self.instance and states is not None:
            if not self.instance.state in \
                   [s.strip() for s in states.split(',')]:
                return []
        html = super(OpenERPFormView, self)._html_button(button)
        html.insert(-1, button.attrib['string'])
        return html

    def _html_notebook(self, notebook):
        html = ['<div class="form_notebook" style="', self.get_width(notebook),
                '"><ul>']
        for page in notebook.iterchildren():
            if self.check_invisible(page):
                continue
            li = '<li>'
            html.extend(['<li>', page.attrib['string'], '</li>'])
        html.append('</ul>')
        html.extend(self._create_html(notebook))
        html.append('</div>')
        return html

    def _html_page(self, page):
        html = ['<div class="form_page" ',
                ' style="display:none;"' if self.check_invisible(page) else '',
                '>']
        html.extend(self._create_html(page))
        html.append('</div>')
        return html

    def _create_html(self, element):
        html = []
        for child in element.iterchildren():
            if isinstance(child, etree._Comment):
                continue
            child_html = getattr(self, '_html_%s' % child.tag)(child)
            html.extend(child_html)
        return  html

    def render(self):
        rend = render_to_string(self.template, {'form_view': self,
                                                'csrf_token': self.csrf_token})
        return {'view_html': rend}
