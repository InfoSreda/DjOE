import base64, datetime
from lxml import etree
from django.db import models
from django.shortcuts import render_to_response
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.template import RequestContext
from django.shortcuts import get_object_or_404, redirect
from django.core.urlresolvers import reverse
from django.views.generic.detail import SingleObjectTemplateResponseMixin
from django.views.decorators.csrf import csrf_exempt
from django.utils import simplejson
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth import views as auth_views

from djoe.base.backends import OpenERPException
from djoe.client.forms import (OpenERPTreeView, OpenERPSearchView,
                               OpenERPFormView)

from djoe.client.auth_forms import OpenERPAuthFormWithSelectDB


class OpenERPWebClientSite(object):

    authentication_form = OpenERPAuthFormWithSelectDB

    index_view_template = 'djoe/client/index.html'
    section_view_template = 'djoe/client/section.html'

    form_view_class = OpenERPFormView
    tree_view_class = OpenERPTreeView
    search_view_class = OpenERPSearchView

    def wrapp_view(self, meth):

        def wrapper(request, *args, **kwargs):
            view = login_required(meth, login_url=reverse('djoe_client:login'))
            return view(request, *args, **kwargs)

        if getattr(meth, 'jsonable', False):
            wrapper = self.json_decor(wrapper)

        if not getattr(meth, 'cacheable', False):
            wrapper = never_cache(wrapper)

        # We add csrf_protect here so this function can be used as a utility
        # function for any view, without having to repeat 'csrf_protect'.
        if not getattr(meth, 'csrf_exempt', False):
            wrapper = csrf_protect(wrapper)
        return wrapper

    def json_decor(self, func):
        def json_wrapp(*args, **kwargs):
            status = 200
            try:
                result = func(*args, **kwargs)
                if isinstance(result, HttpResponseRedirect):
                    # login_required redirect
                    # TODO: login_required validation use in that decorator
                    status = 403
                    result = {'_redirect': result['location']}
                elif isinstance(result, HttpResponse):
                    return result
                assert isinstance(result, dict)
            except Exception, exc:
                status = 404 if isinstance(exc, Http404) else 500
                if hasattr(exc, 'as_html'):
                    mess = exc.as_html()
                else:
                    raise
                result = {'error': mess}
            json = simplejson.dumps(result)
            resp = HttpResponse(json, mimetype='application/json',
                                status=status)
            return resp
        return json_wrapp

    def get_urls(self):
        from django.conf.urls.defaults import patterns, url, include

        # auth urls
        urlpatterns = patterns('',
            url(r'^login/$', auth_views.login, kwargs=dict(
                                   template_name='djoe/client/login.html',
               authentication_form=self.authentication_form), name='login'),
            url(r'^logout/$', auth_views.logout_then_login, name='logout'),
                               )

        urlpatterns += patterns('',
           url(r'^$',
               self.wrapp_view(self.index_view),
               name="index"),
           url(r'^section/(?P<section_id>\d+)/$',
               self.wrapp_view(self.section_view),
               name="section"),
                            
           url(r'^section/\d+/menu/(?P<menu_id>\d+)/$',
               self.wrapp_view(self.menu_view),
               name="menu"),

           url(r'^get_view/$',
               self.wrapp_view(self.getview_view),
               name="menu"),

           url(r'^edit/(?P<oe_model>[\w\.]+)/get/(?P<object_id>\d+)/$',
               self.wrapp_view(self.edit_view), name="object_edit"),
           url(r'^edit/(?P<oe_model>[\w\.]+)/get/(?P<object_id>\d+)/form/(?P<form_view_id>\d+)/$',
               self.wrapp_view(self.edit_view),
               name="object_edit_with_view"),

                                # OLD VIEWS

           url(r'^section/(?P<section_id>\d+)/menu/(?P<menu_id>\d+)/$',
               self.wrapp_view(self.submenu_view),
               name="submenu"),

           url(r'^section/(?P<section_id>\d+)/menu/(?P<menu_id>\d+)/edit/(?P<object_id>\d+)/$',
               self.wrapp_view(self.edit_view),
               name="object_edit"),
           url(r'^ajax/(?P<oe_model>[\w\.]+)/get_name/(?P<object_id>\d+)/$',
               self.wrapp_view(self.ajax_get_name_view),
               name="ajax_object_get_name"),
           url(r'^ajax/(?P<oe_model>[\w\.]+)/get/(?P<object_id>\d+)/$',
               self.wrapp_view(self.ajax_edit_view), name="ajax_object_edit"),
           url(r'^ajax/(?P<oe_model>[\w\.]+)/get/(?P<object_id>\d+)/form/(?P<form_view_id>)/$',
               self.wrapp_view(self.ajax_edit_view),
               name="ajax_object_edit_with_view"),
           url(r'^ajax/(?P<oe_model>[\w\.]+)/add/$',
               self.wrapp_view(self.ajax_edit_view),
               name="ajax_object_new"),
           url(r'^ajax/(?P<oe_model>[\w\.]+)/search/$',
               self.wrapp_view(self.ajax_search_view),
               name="ajax_object_search"),
           url(r'^ajax/(?P<oe_model>[\w\.]+)/search/tree/(?P<tree_view_id>\d+)/search/(?P<search_view_id>\d+)/$',
               self.wrapp_view(self.ajax_search_view),
               name="ajax_object_search_with_views"),
           url(r'^section/(?P<section_id>\d+)/menu/(?P<menu_id>\d+)/add/$',
               self.wrapp_view(self.edit_view), name="object_new"),
           url(r'^section/(?P<section_id>\d+)/menu/(?P<menu_id>\d+)/delete/$',
               self.wrapp_view(self.delete_view),
               name="object_delete"),
           url(r'^section/(?P<section_id>\d+)/menu/(?P<menu_id>\d+)/details/(?P<object_id>\d+)/$',
               self.wrapp_view(self.details_view), name="object_details"),
                                )

        urlpatterns += patterns('', (r'^media/', include('djoe.base.urls')) )
        return urlpatterns

    @property
    def urls(self):
        return self.get_urls(), 'djoe_client', 'djoe_client'

    # VIEWS
    def index_view(self, request):
        act_window = request.user.get_model('ir.actions.act_window').objects.\
                     get(id=request.user.menu_id)
        Menu = request.user.get_model('ir.ui.menu')
        sections = Menu.objects.filter(parent_id__isnull=True)
        return render_to_response(self.index_view_template,
                              {'section_list': sections},
                              context_instance=RequestContext(request))

    def get_menu_childs(self, qs):
        qs_dict = dict( ( (item.pk, item) for item in qs))
        childs = qs.model.objects.filter(parent_id__in=qs_dict.keys())
        if childs:
            childs = self.get_menu_childs(childs)
            for ch in childs:
                if not hasattr(qs_dict[ch.parent_id.pk], 'childrens'):
                    qs_dict[ch.parent_id.pk].childrens = []
                qs_dict[ch.parent_id.pk].childrens.append(ch)
        return qs

    def section_view(self, request, section_id):
        Menu = request.user.get_model('ir.ui.menu')
        section = get_object_or_404(Menu, id=section_id)
        sections = Menu.objects.filter(parent_id__isnull=True)
        menu_list = self.get_menu_childs(Menu.objects.filter(parent_id=section))
        return render_to_response(self.section_view_template,
                              {'section_list': sections,
                               'menu_list': menu_list,
                               'current_section': section},
                              context_instance=RequestContext(request))

    def menu_view(self, request, menu_id):
        menu_id = int(menu_id)
        ctx = request.user.get_default_context()
        menu_action = request.user.objects('ir.values', 'get', 'action',
                             'tree_but_open', [('ir.ui.menu', menu_id)], False,
                                     ctx)[0][2]
        model_name = menu_action['res_model']
        ItemModel = request.user.get_model(model_name)

        views = menu_action['views']
        view_type = views[0][1]

        ViewClass = getattr(self, '%s_view_class' % view_type)
        search_view_id = menu_action['search_view_id'][0] \
                         if menu_action['search_view_id'] else None

        kwargs = dict(model_class=ItemModel,
                      view_id=views[0][0],
                      search_view_id=search_view_id,
                      with_edit=True)
        if view_type == 'form':
            kwargs['instance'] = ItemModel.objects.oe_default_get(context=ctx)
        view = ViewClass(**kwargs)
        views = dict(( (v[1], v[0]) for v in views))
        result = {
            'target':  menu_action['target'],
            'name': menu_action['name'],
            'help': menu_action['help'],
            'views': views,
            'view_type': view_type,
            'model': model_name
            }
        result.update(view.render())
        if search_view_id:
            initial = request.user.objects('ir.filters', 'get_filters',
                                           model_name)
            print '%%%%%%%%%%%%%', initial
            search_view = OpenERPSearchView(model_class=ItemModel,
                                        view_id=search_view_id)
            search_view.get_html()
            result.update(search_view.render())
        return result
    menu_view.jsonable = True

    def getview_view(self, request):
        ctx = request.user.get_default_context()

        model_name = request.GET['model']
        ItemModel = request.user.get_model(model_name)

        view_type = request.GET['type']
        try:
            view_id = int(request.GET['id'])
        except:
            view_id = None
        ViewClass = getattr(self, '%s_view_class' % view_type)

        kwargs = dict(model_class=ItemModel,
                      view_id=view_id,
                      with_edit=True)
        if view_type == 'form':
            kwargs['csrf_token'] = get_token(request)

            if 'object_id' in request.GET:
                kwargs['instance'] = ItemModel.objects.get(id=request.GET['object_id'])
            else:
                kwargs['instance'] = ItemModel.objects.oe_default_get(context=ctx)
        view = ViewClass(**kwargs)
        result = {
            'view_type': view_type,
            'model': model_name
            }
        #print view.get_html()
        result.update(view.render())
        return result
    getview_view.jsonable = True

    def edit_view(self, request, oe_model, object_id=None,
                       form_view_id=False):
        object_id = int(object_id)
        ItemModel = request.user.get_model(str(oe_model))
        ctx = request.user.get_default_context()

        if object_id:
            item = get_object_or_404(ItemModel, id=object_id)
        else:
            item = None

        if not request.POST:
            raise Http404
        
        form_view = OpenERPFormView(model_class=ItemModel,
                                    instance=item,
                                    data=request.POST,
                                    view_id=form_view_id)
        #form_view.remove_notview_model_fields()
        data = {'id': object_id or 0}
        if form_view.is_valid():
            inst = form_view.save()
            data['id'] = inst.id
            data['save'] = True
        else:
            errs = {}
            for k, v in form_view.errors.iteritems():
                errs[k] = u'%s: %s' % (form_view.form[k].label, v)
            data['errors'] = errs
        return data
    edit_view.jsonable = True
















    def submenu_view(self, request, section_id, menu_id):
        menu_id = int(menu_id)
        ctx = request.user.get_default_context()
        klass = request.user.objects('ir.values', 'get', 'action',
                             'tree_but_open', [('ir.ui.menu', menu_id)], False,
                                     ctx)[0][2]
        model_name = klass['res_model']
        ItemModel = request.user.get_model(model_name)

        tree_view_id = klass['view_id'] and klass['view_id'][0]
        search_view_id = klass['search_view_id'] and klass['search_view_id'][0]

        tree_view = OpenERPTreeView(model_class=ItemModel,
                                    view_id=tree_view_id,
                                    search_view_id=search_view_id,
                                    with_edit=True)

        print tree_view.get_html()
        if request.is_ajax():
            pass
        Menu = request.user.get_model('ir.ui.menu')
        section = get_object_or_404(Menu, id=section_id)
        menu = get_object_or_404(Menu, id=menu_id)
        sections = Menu.objects.filter(parent_id__isnull=True)
        menu_list = self.get_menu_childs(Menu.objects.filter(parent_id=section))

        search_view = OpenERPSearchView(model_class=ItemModel,
                                        view_id=search_view_id)

        return render_to_response('djoe/client/submenu.html',
                                  {'section_list': sections,
                                   'menu_list': menu_list,
                                   'current_section': section,
                                   'current_menu': menu,
                                   'klass':klass,
                                   'tree_view':tree_view,
                                   'search_view':search_view},
                                  context_instance=RequestContext(request))

    def ajax_search_view(self, request, oe_model, tree_view_id=False,
                    search_view_id=False):
        get_data = request.GET.copy()
        get_data.pop('_', None)
        ItemModel = request.user.get_model(str(oe_model))

        ctx = request.user.get_default_context()

        tree_view = OpenERPTreeView(model_class=ItemModel,
                                    view_id=tree_view_id,
                                    search_view_id=search_view_id,
                                    with_edit='_with_edit' in get_data)

        search_view = OpenERPSearchView(model_class=ItemModel,
                                        view_id=search_view_id)

        if not get_data:    
            return render_to_response("djoe/client/tree_view.html",
                                  {'tree_view': tree_view,
                                   'search_view': search_view},
                                  context_instance=RequestContext(request))
        n = 0
        order_by = []
        dir_dict  = {'asc':'', 'desc':'-'}
        while True:
            sort_field = get_data.get('sort[%d][field]' % n)
            sort_dir = get_data.get('sort[%d][dir]' % n)
            if not sort_field and not sort_dir:
                break
            order_by.append('%s%s' % (dir_dict[sort_dir], sort_field) )
            n += 1
        try:
            page = int(get_data.get('page', '1'))
        except ValueError:
            page = 1

        try:
            per_page = int(get_data.get('pageSize', '40'))
        except ValueError:
            per_page = 40
        item_list = ItemModel.objects.all().only(*tree_view.fields.keys())

        if order_by:
            item_list = item_list.order_by(*order_by)
        paginator = Paginator(item_list, per_page) 

        try:
            items = paginator.page(page)
        except (EmptyPage, InvalidPage):
            items = paginator.page(1)

        data = []                    
        tree_view.get_html()

        for item in items.object_list:
            row = {'__id': item.id}
            item_args = {}
            for f in (f['field'] for f in tree_view.headers):
                if f is None:
                    val = ''
                else:
                    val = getattr(item, f)
                if isinstance(val, datetime.datetime):
                    val = val.strftime('%Y-%m-%d %H:%M:%S')
                elif isinstance(val, models.Model):
                    val = unicode(val)
                row[f] = val
                row['__color'] = tree_view.get_color(row)
            data.append( row )

        return HttpResponse(simplejson.dumps({'data': data,
                                              'total': item_list.count()}))

    def ajax_get_name_view(self, request, oe_model, object_id):
        ctx = request.user.get_default_context()
        name = request.user.objects(oe_model, 'name_get', [object_id], ctx)
        return HttpResponse(u'{"name":"%s"}' % name[0][1])

    def ajax_edit_view(self, request, oe_model, object_id=None,
                       form_view_id=False):
        ItemModel = request.user.get_model(str(oe_model))
        ctx = request.user.get_default_context()

        if object_id:
            item = get_object_or_404(ItemModel, id=object_id)
        else:
            item = None
        #print form_view['arch']

        if request.POST:
            form_view = OpenERPFormView(model_class=ItemModel,
                                        instance=item,
                                        data=request.POST,
                                        view_id=form_view_id)
            data = {'id': object_id or 0}
            if form_view.is_valid():
                try:
                    form_view.save()
                except OpenERPException, e:
                    data['errors'] = {'': e.as_html()}
                else:
                    data['href'] = '../../'
            else:
                errs = {}
                for k, v in form_view.errors.iteritems():
                    if k.startswith('_'):
                        continue
                    errs[k] = u'%s: %s' % (form_view.form[k].label, v)
                data['errors'] = errs
            return HttpResponse(simplejson.dumps(data))
        else:
            form_view = OpenERPFormView(model_class=ItemModel, instance=item,
                                        view_id=form_view_id)
        return render_to_response("djoe/client/form_view.html",
                                  {'form_view':form_view},
                                  context_instance=RequestContext(request))

    def old_edit_view(self, request, section_id, menu_id, object_id=None):
        menu_id = int(menu_id)
        ctx = request.user.get_default_context()

        klass = request.user.objects('ir.values', 'get', 'action',
                             'tree_but_open', [('ir.ui.menu', menu_id)])[0][2]
        model_name = klass['res_model']
        ItemModel = request.user.get_model(model_name)
        if object_id:
            item = get_object_or_404(ItemModel, id=object_id)
        else:
            item = None
        if request.POST:
            form_view = OpenERPFormView(model_class=ItemModel,
                                        instance=item,
                                        data=request.POST,
                                        view_id=False)
            print '@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@'
            print form_view.form.data
            if form_view.is_valid():
                print form_view.form.cleaned_data
                form_view.save()
                #raise
                return redirect('submenu', section_id=section_id,
                                menu_id=menu_id)
        else:
            form_view = OpenERPFormView(model_class=ItemModel,
                                        instance=item, view_id=False)

        Menu = request.user.get_model('ir.ui.menu')
        section = get_object_or_404(Menu, id=section_id)
        menu = get_object_or_404(Menu, id=menu_id)
        sections = Menu.objects.filter(parent_id__isnull=True)
        menu_list = self.get_menu_childs(Menu.objects.filter(parent_id=section))
        return render_to_response('djoe/client/edit.html',
                                  {'section_list': sections,
                                   'menu_list': menu_list,
                                   'current_section': section,
                                   'current_menu': menu,
                                   'form_view':form_view},
                                  context_instance=RequestContext(request))

    def delete_view(self, request, section_id, menu_id, object_id):
        menu_id = int(menu_id)

        klass = request.user.objects('ir.values', 'get', 'action',
                             'tree_but_open', [('ir.ui.menu', menu_id)])[0][2]
        model_name = klass['res_model']
        ItemModel = request.user.get_model(model_name)

        item = get_object_or_404(ItemModel, id=object_id)
        item.delete()
        return redirect('submenu', section_id=section_id, submenu_id=submenu_id)

    def details_view(self, request, section_id, menu_id, object_id):
        menu_id = int(menu_id)

        klass = request.user.objects('ir.values', 'get', 'action',
                             'tree_but_open', [('ir.ui.menu', menu_id)])[0][2]
        model_name = klass['res_model']
        ItemModel = request.user.get_model(model_name)

        item = get_object_or_404(ItemModel, id=object_id)

        form_view = request.user.objects(model_name, 'fields_view_get', False,
                                         'form')
        form_arch = form_view['arch']

        get_form(ItemModel, search_fields)()

        Menu = request.user.get_model('ir.ui.menu')
        section = get_object_or_404(Menu, id=section_id)
        menu = get_object_or_404(Menu, id=menu_id)
        sections = Menu.objects.filter(parent_id__isnull=True)
        menu_list = self.get_menu_childs(Menu.objects.filter(parent_id=section))

        return render_to_response('djoe/client/submenu.html',
                                  {'section_list': sections,
                                   'menu_list': menu_list,
                                   'current_section': section,
                                   'current_menu': menu,
                                   'klass':klass,
                                   'tree_columns':tree_columns,
                                   'search_form':search_form},
                                  context_instance=RequestContext(request))

oe_site = OpenERPWebClientSite()
