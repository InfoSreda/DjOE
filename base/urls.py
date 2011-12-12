from django.conf.urls.defaults import *

urlpatterns = patterns('',
      url(r'^(?P<model>[\w\.]+)/(?P<object_id>\d+)/(?P<field>\w+)/$',
        'djoe.base.views.media', name="djoe_base_media")
)
