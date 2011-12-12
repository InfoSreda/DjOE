from django.contrib import admin
from example.models import *


class OpenStateAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'country_id')


admin.site.register(OpenCountry)
admin.site.register(OpenState, OpenStateAdmin)

