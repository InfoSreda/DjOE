import base64
import datetime
from lxml import etree
from django.shortcuts import render_to_response
from django.http import HttpResponse
from django.template import RequestContext
from django.shortcuts import get_object_or_404, redirect
from django.core.urlresolvers import reverse
from django.views.generic import (View, ListView, DetailView,
                                  CreateView, UpdateView, DeleteView)
from django.views.generic.detail import SingleObjectTemplateResponseMixin
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils import simplejson
from django.db import models
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django import forms
from djoe.base.backends import OpenERPException
from djoe.client.forms import (OpenERPTreeView, OpenERPSearchView,
                               OpenERPFormView)


@login_required
def main(request):
    act_window = request.user.get_model('ir.actions.act_window').objects.\
                 get(id=request.user.menu_id)
    #user_menu = request.user.get_model('ir.actions.act_window').filter()
    Menu = request.user.get_model('ir.ui.menu')
    sections = Menu.objects.filter(parent_id__isnull=True)
    return render_to_response('djoe/client/main_page.html',
                              {'section_list': sections},
                              context_instance=RequestContext(request))


def get_menu_childs(qs, cls):
    qs_dict = dict( ( (item.pk, item) for item in qs))
    childs = cls.objects.filter(parent_id__in=qs_dict.keys())
    if childs:
        childs = get_menu_childs(childs, cls)
        for ch in childs:
            if not hasattr(qs_dict[ch.parent_id.pk], 'childrens'):
                qs_dict[ch.parent_id.pk].childrens = []
            qs_dict[ch.parent_id.pk].childrens.append(ch)
    return qs

@login_required
def section(request, section_id):
    Menu = request.user.get_model('ir.ui.menu')
    section = get_object_or_404(Menu, id=section_id)
    sections = Menu.objects.filter(parent_id__isnull=True)
    menu_list = get_menu_childs(Menu.objects.filter(parent_id=section), Menu)
    return render_to_response('djoe/client/section.html',
                              {'section_list': sections,
                               'menu_list': menu_list,
                               'current_section':  section},
                              context_instance=RequestContext(request))

@login_required
def submenu(request, section_id, menu_id):
    menu_id = int(menu_id)
    ctx = request.user.get_default_context()
    klass = request.user.objects('ir.values', 'get', 'action',
                         'tree_but_open', [('ir.ui.menu', menu_id)], False,
                                 ctx)[0][2]
    model_name = klass['res_model']
    ItemModel = request.user.get_model(model_name)

    """
    print '------' * 10
    for f in ItemModel._meta.fields:
        print f.name, ' :: ', f
    print '*****' * 10
    for f in ItemModel._meta.get_all_related_objects():
        print f.name, f.get_accessor_name()
    print '$' * 70
    """
    tree_view_id = klass['view_id'] and klass['view_id'][0]
    search_view_id = klass['search_view_id'] and klass['search_view_id'][0]
    
    tree_view = OpenERPTreeView(model_class=ItemModel,
                                view_id=tree_view_id,
                                search_view_id=search_view_id,
                                with_edit=True)

    #print '^' * 70
    #print tree_view.get_html()
    if request.is_ajax():
        pass
    Menu = request.user.get_model('ir.ui.menu')
    section = get_object_or_404(Menu, id=section_id)
    menu = get_object_or_404(Menu, id=menu_id)
    sections = Menu.objects.filter(parent_id__isnull=True)
    menu_list = get_menu_childs(Menu.objects.filter(parent_id=section),
                                    Menu)

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


@login_required
def ajax_search(request, oe_model, tree_view_id=False, search_view_id=False):
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
    item_list = ItemModel.objects.all()

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


@login_required
def ajax_get_name(request, oe_model, object_id):
    ctx = request.user.get_default_context()
    name = request.user.objects(oe_model, 'name_get', [object_id],
                                ctx)

    return HttpResponse(u'{"name":"%s"}' % name[0][1])

@login_required
def ajax_edit(request, oe_model, object_id=None, form_view_id=False):
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


@login_required
def edit(request, section_id, menu_id, object_id=None):
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
        print 333333333333333333333
        print form_view.errors
    else:
        form_view = OpenERPFormView(model_class=ItemModel,
                                    instance=item, view_id=False)

    Menu = request.user.get_model('ir.ui.menu')
    section = get_object_or_404(Menu, id=section_id)
    menu = get_object_or_404(Menu, id=menu_id)
    sections = Menu.objects.filter(parent_id__isnull=True)
    menu_list = get_menu_childs(Menu.objects.filter(parent_id=section),
                                Menu)
    print form_view.get_html()
    return render_to_response('djoe/client/edit.html',
                              {'section_list': sections,
                               'menu_list': menu_list,
                               'current_section': section,
                               'current_menu': menu,
                               'form_view':form_view},
                              context_instance=RequestContext(request))

@login_required
def delete(request, section_id, menu_id, object_id):
    menu_id = int(menu_id)

    klass = request.user.objects('ir.values', 'get', 'action',
                         'tree_but_open', [('ir.ui.menu', menu_id)])[0][2]
    model_name = klass['res_model']
    ItemModel = request.user.get_model(model_name)

    item = get_object_or_404(ItemModel, id=object_id)
    item.delete()
    return redirect('submenu', section_id=section_id, submenu_id=submenu_id)


@login_required
def details(request, section_id, menu_id, object_id):
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
    menu_list = get_menu_childs(Menu.objects.filter(parent_id=section),
                                Menu)

    return render_to_response('djoe/client/submenu.html',
                              {'section_list': sections,
                               'menu_list': menu_list,
                               'current_section': section,
                               'current_menu': menu,
                               'klass':klass,
                               'tree_columns':tree_columns,
                               'search_form':search_form},
                              context_instance=RequestContext(request))

