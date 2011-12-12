from django.conf.urls.defaults import patterns, include, url
from django.views.generic.list_detail import object_list, object_detail
from djoe.base.backends import oe_session


# TODO: Tuples should be replaced with url() function.
# TODO: Replace it with class-based generic views.
oe_session.get_model('product.category')


urlpatterns = patterns('',
    url(r'^$', object_list, {
        'queryset': oe_session.get_model('product.product').objects.filter(active=True),
        'template_name': 'store/list.html',
        'template_object_name': 'product',
        'paginate_by': 10,
        'page': 1,
        }, name='store'),
    url(r'^products/(?P<object_id>[-a-z0-9]+)/$', object_detail, {
        'queryset': oe_session.get_model('product.product').objects.filter(active=True),
        'template_name': 'store/detail.html',
        'template_object_name': 'product'
        }, name='product'),
)
