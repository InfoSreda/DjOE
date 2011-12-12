from django import forms
from django import forms
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate
from djoe.base.backends import oe_session


class OpenERPAuthForm(AuthenticationForm):

    database = forms.CharField(label=_("Database"), max_length=30)

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        database = self.cleaned_data.get('database')

        if username and password:
            self.user_cache = authenticate(username=username,
                                           password=password,
                                           database=database)
            if self.user_cache is None:
                raise forms.ValidationError(_("Please enter a correct username'\
                  'and password. Note that both fields are case-sensitive."))
        self.check_for_test_cookie()
        return self.cleaned_data


class OpenERPAuthFormWithSelectDB(OpenERPAuthForm):

    database = forms.ChoiceField(label=_("Database"))

    def __init__(self, *args, **kwargs):
        super(OpenERPAuthFormWithSelectDB, self).__init__(*args, **kwargs)
        databases = oe_session.execute('db', 'list')
        self.fields['database'].choices = [(d,d) for d in databases]
