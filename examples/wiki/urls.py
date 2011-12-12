from django.conf.urls.defaults import patterns, include, url
from django.views.generic.list_detail import object_list, object_detail
from djoe.base.backends import oe_session


oe_session.get_model('wiki.groups')


urlpatterns = patterns('djoe.examples.wiki.views',
    url(r'^$', object_list, {
        'queryset': oe_session.get_model('wiki.wiki').objects.all(),
        'template_name': 'wiki/list.html',
        'template_object_name': 'wiki',
        }, name='wiki'),
    url(r'^pages/(?P<object_id>[-a-z0-9]+)/$', 'wiki_page', name='wiki_page')
)
