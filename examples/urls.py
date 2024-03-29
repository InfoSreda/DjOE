from django.conf.urls.defaults import patterns, include, url
from django.views.generic.simple import direct_to_template


urlpatterns = patterns('',
    url(r'^$', direct_to_template, {
        'template': 'index.html',
        }, name='examples'),
    url(r'^store/', include('djoe.examples.store.urls')),
    #url(r'^wiki/', include('djoe.examples.wiki.urls')),
)
