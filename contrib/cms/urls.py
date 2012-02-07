from django.conf.urls.defaults import patterns, include, url


urlpatterns = patterns('djoe.contrib.cms.views',
    url(r'^cms/media/(?P<path>.+)$', 'cms_media', name="cms_media"),
    url(r'^(?P<path>[\w\/-]*)$', 'cms', name='cms'),
)
