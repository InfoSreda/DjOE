from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib.auth.views import login, logout_then_login
from djoe.client.auth_forms import OpenERPAuthFormWithSelectDB



urlpatterns = patterns('',
    url(r'^login/$', login, kwargs=dict(
        template_name='djoe/client/login.html',
        authentication_form=OpenERPAuthFormWithSelectDB), name='login'),
    url(r'^logout/$', logout_then_login, name='logout'),
)

urlpatterns += patterns('',
    url(r'^$', 'djoe.client.views.main', name="main"),
    url(r'^section/(?P<section_id>\d+)$', 'djoe.client.views.section',
        name="section"),
    url(r'^section/(?P<section_id>\d+)/menu/(?P<menu_id>\d+)/$',
        'djoe.client.views.submenu', name="submenu"),

    url(r'^section/(?P<section_id>\d+)/menu/(?P<menu_id>\d+)/edit/(?P<object_id>\d+)/$',
        'djoe.client.views.edit', name="object_edit"),

    url(r'^ajax/(?P<oe_model>[\w\.]+)/get_name/(?P<object_id>\d+)/$',
        'djoe.client.views.ajax_get_name', name="ajax_object_get_name"),

    url(r'^ajax/(?P<oe_model>[\w\.]+)/get/(?P<object_id>\d+)/$',
        'djoe.client.views.ajax_edit', name="ajax_object_edit"),

    url(r'^ajax/(?P<oe_model>[\w\.]+)/get/(?P<object_id>\d+)/form/(?P<form_view_id>)/$',
        'djoe.client.views.ajax_edit', name="ajax_object_edit_with_view"),


    url(r'^ajax/(?P<oe_model>[\w\.]+)/add/$',
        'djoe.client.views.ajax_edit', name="ajax_object_new"),

    url(r'^ajax/(?P<oe_model>[\w\.]+)/search/$',
        'djoe.client.views.ajax_search', name="ajax_object_search"),

    url(r'^ajax/(?P<oe_model>[\w\.]+)/search/tree/(?P<tree_view_id>\d+)/search/(?P<search_view_id>\d+)/$',
        'djoe.client.views.ajax_search', name="ajax_object_search_with_views"),


    url(r'^section/(?P<section_id>\d+)/menu/(?P<menu_id>\d+)/add/$',
        'djoe.client.views.edit', name="object_new"),

    url(r'^section/(?P<section_id>\d+)/menu/(?P<menu_id>\d+)/delete/$',
        'djoe.client.views.delete', name="object_delete"),

    url(r'^section/(?P<section_id>\d+)/menu/(?P<menu_id>\d+)/details/(?P<object_id>\d+)/$',
        'djoe.client.views.details', name="object_details"),
)

urlpatterns += patterns('', (r'^media/', include('djoe.base.urls')) )

'''
urlpatterns += patterns('',
    url(r'(?P<model_key>[\w\/]+)/list/$', get_view('list'),
        name="list"),
    url(r'(?P<model_key>[\w\/]+)/(?P<pk>\d+)/detail/$',
        view_by_class(ObjectDetail), name="detail"),

    url(r'(?P<model_key>\w[\/]+)/create/$', view_by_class(ObjectCreate),
        name="create"),
    url(r'(?P<model_key>\w[\/]+)/(?P<pk>\d+)/update/$',
        view_by_class(ObjectUpdate), name="update"),

    url(r'(?P<model_key>[\w\/]+)/(?P<pk>\w+)/delete/$',
        view_by_class(ObjectDelete), name="delete"),
    url(r'(?P<model_key>\w+)/(?P<pk>\w+)/comment/$',
        login_required(ObjectComment.as_view()),
        name="comment"),

    url(r'(?P<model_key>\w+)/create/add/form/$', ObjectAddForm.as_view(),
        name="add_create_form"),

    url(r'(?P<model_key>\w+)/(?P<pk>\w+)/update/add/form/$',
        ObjectAddForm.as_view(), name="add_update_form"),
)
'''
