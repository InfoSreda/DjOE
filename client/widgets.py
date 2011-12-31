import datetime
from django.utils.safestring import mark_safe
from django.utils.encoding import force_unicode
from django.db import models
from django import forms
from django.template.loader import render_to_string
from django.core import validators

from django.core.urlresolvers import reverse


class DateFieldWidget(forms.DateInput):

    def __init__(self, *args, **kwargs):
        super(DateFieldWidget, self).__init__(*args, **kwargs)
        self.attrs.update({'class': 'date_widget'})


class OECheckboxInput(forms.CheckboxInput):

    def value_from_datadict(self, data, files, name):
        if name not in data:
            # A missing value means False because HTML form submission does not
            # send results for unselected checkboxes.
            return False
        value = data.get(name)
        # Translate true and false strings to boolean values.
        values =  {'true': True, 'false': False,
                   'on': True, 'off': False,
                   '': False}
        if isinstance(value, basestring):
            value = values.get(value.lower(), value)
        return value


class OEHiddenInput(forms.HiddenInput):

    def render(self, name, value, attrs=None):
        if hasattr(value, 'pk'):
            value = value.pk
        return super(OEHiddenInput, self).render(name, value, attrs)


class OEManyToOneWidget(forms.HiddenInput):

    def render(self, name, value, attrs=None):
        print value
        oe_model = value._openerp_model
        edit_url = reverse('djoe_client:ajax_object_edit', args=(oe_model, 0))
        search_url = reverse('djoe_client:ajax_object_search', args=(oe_model,))
        get_name_url = reverse('djoe_client:ajax_object_get_name', args=(oe_model, 0,))

        html = ['<span class="m2o_field" oe_model="%s" get_name="%s">' % \
                (oe_model, get_name_url),

            super(OEManyToOneWidget, self).render(name, value.pk, attrs),
               u'<span><input type="text" value="%s" class="m2o_title"/></span>' % \
                value.name_get(),
                '<a class="k-icon k-maximize" href="%s"' % edit_url,
                '' if value.pk else ' style="display:none"',
                '></a>',
                '<a class="k-icon k-search" href="%s"></span>' % search_url,
                '</a>']
        return mark_safe(''.join(html))


class OEManyToManyWidget(forms.MultipleHiddenInput):

    def render(self, name, value, attrs=None):
        from djoe.client.forms import OpenERPTreeView
        tree_view = OpenERPTreeView(model_class=value[0].__class__)
        value_ids = [i.pk for i in value if i.pk]
        super_html = super(OEManyToManyWidget, self).render(name,
                                                           value_ids, attrs)

        for item in items.object_list:
            row = {'id':item.pk, 'fields': []}
            for f in (f['field'] for f in tree_view.headers):
                if f is None:
                    val = ''
                else:
                    val = getattr(item, f)
                if isinstance(val, datetime.datetime):
                    val = val.strftime('%Y-%m-%d %H:%M:%S')
                elif isinstance(val, models.Model):
                    val = unicode(val)
                row['fields'].append(val)
            row['color'] = tree_view.get_color(row['fields'])
            rows.append(row)

        html = render_to_string('djoe/client/tree_grid.html',
                                {'tree_view': tree_view,
                                 'hidden_html': super_html,
                                 'static': True,
                                 'rows': rows})
        return html


    def render(self, name, value, attrs=None):
        from djoe.client.forms import OpenERPTreeView
        tree_view = OpenERPTreeView(model_class=value[0].__class__)
        value_ids = [i.pk for i in value if i.pk]
        super_html = super(OEManyToManyWidget, self).render(name,
                                                           value_ids, attrs)

        rows = []
        for item in value:
            row = {'id':item.pk, 'fields': []}
            for f in (f['field'] for f in tree_view.headers):
                if f is None:
                    val = ''
                else:
                    val = getattr(item, f)
                if isinstance(val, datetime.datetime):
                    val = val.strftime('%Y-%m-%d %H:%M:%S')
                elif isinstance(val, models.Model):
                    val = unicode(val)
                row['fields'].append(val)
            row['color'] = tree_view.get_color(row['fields'])
            rows.append(row)

        html = render_to_string('djoe/client/tree_grid.html',
                                {'tree_view': tree_view,
                                 'hidden_html': super_html,
                                 'static': True,
                                 'rows': rows})
        return html


class OEOneToManyWidget(forms.MultipleHiddenInput):

    def render(self, name, value, attrs=None):
        from djoe.client.forms import OpenERPTreeView
        tree_view = OpenERPTreeView(model_class=value[0].__class__,
                                    with_edit=True)
        value_ids = [i.pk for i in value if i.pk]
        super_html = super(OEOneToManyWidget, self).render(name,
                                                           value_ids, attrs)

        rows = []
        tree_view.get_html()
        for item in value:
            row = {'id':item.pk, 'fields': []}
            for f in (f['field'] for f in tree_view.headers):
                if f is None:
                    val = ''
                else:
                    try:
                        val = getattr(item, f)
                    except:
                        # TODO!!!
                        val = ''
                if isinstance(val, datetime.datetime):
                    val = val.strftime('%Y-%m-%d %H:%M:%S')
                elif isinstance(val, models.Model):
                    val = unicode(val)
                row['fields'].append(val)
            row['color'] = tree_view.get_color(row['fields'])
            rows.append(row)

        html = render_to_string('djoe/client/tree_grid.html',
                                {'tree_view': tree_view,
                                 'hidden_html': super_html,
                                 'static': True,
                                 'rows': rows})
        return html


class OEBaseRelationField(forms.Field):

    def __init__(self, model, *args, **kwargs):
        super(OEBaseRelationField, self).__init__(*args, **kwargs)
        self.model = model

    def prepare_value(self, value):
        # mustbe instance of models.Model
        print '@@@@@@@@@@@@@@@@@@@', value, type(value)
        if not value:
            value = self.model(None)
        elif isinstance(value, (int, long, basestring)):
            value = self.model.objects.get(pk=value)
        return value

    def to_python(self, value):
        if value in validators.EMPTY_VALUES:
            return None
        try:
            value = self.model.objects.get(pk=value)
        except self.model.DoesNotExist:
            raise ValidationError(self.error_messages['invalid_choice'])
        return value


class OEManyToOneField(OEBaseRelationField):
    widget = OEManyToOneWidget


class OEManyToManyField(OEBaseRelationField):
    widget = OEManyToManyWidget

    def prepare_value(self, value):
        # mustbe instance of models.Model
        print '@@@@@@@@@@@@@@@@@@@', value, type(value)
        if not value:
            value = [self.model(None)]
        elif isinstance(value, (list, tuple)):
            value = self.model.objects.filter(pk__in=value)
        return value

    def to_python(self, value):
        if value in validators.EMPTY_VALUES:
            return None
        try:
            value = self.model.objects.filter(pk__in=value)
        except self.model.DoesNotExist:
            raise ValidationError(self.error_messages['invalid_choice'])
        return value


class OEOneToManyField(OEManyToManyField):
    widget = OEOneToManyWidget

    def __init__(self, model, *args, **kwargs):
        super(OEOneToManyField, self).__init__(model, *args, **kwargs)
