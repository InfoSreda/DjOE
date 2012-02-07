import re, datetime
from django.db.models import Q
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse

from django.conf import settings
from djoe.base.backends import oe_session

def _only_published(title_list):
    now = datetime.datetime.now()
    published_title_list = []
    for title in title_list:
        if title.publication_date and title.publication_date > now:
            continue
        if title.publication_end_date and \
               title.publication_end_date < now:
            continue
        published_title_list.append(title)
    return published_title_list


def cms(request):
    path = request.path
    Lang = oe_session.get_model('res.lang')
    langs = Lang.objects.all()

    host = request.get_host()
    site = oe_session.get_model('cms.site').objects.get(host=host)

    Title = oe_session.get_model('cms.title')


    query = Q(page_id__published=True, page_id__in_navigation=True)

    if request.LANGUAGE_ID:
        query &= Q(language_id=request.LANGUAGE_ID)
    else:
        query &= Q(language_id__code=settings.LANGUAGE_CODE)

    w_path = path[1:].split('/')
    if len(w_path[0]) == 2:
        w_path = w_path[1:]

    def get_menu(path, qu='page_id__parent_id__title_ids__path'):
        add_q = {qu: path}
        menu_list = Title.objects.filter(query, **add_q).order_by('page_sequence')
        menu_list = _only_published(menu_list)
        for m in menu_list:
            m.child_menu_list = get_menu(m.path)
            if not m.path.endswith('/'):
                m.path += '/'
        return menu_list

    menu_list = []
    w_path = [p for p in w_path if p]
    w_path.insert(0, '')
    curr_path = ''
    for path in w_path:
        menus = get_menu(path)
        if path:
            if curr_path:
                curr_path += '/%s' % path
            else:
                curr_path = path
            for m in menu_list[-1]:
                if m.path[:-1] == curr_path:
                    m.active_menu = True
        if not menus:
            break
        menu_list.append(menus)

    context_extras = {
        'language_list': langs,
        'menu_list': menu_list
    }

    for pc in oe_session.get_model('cms.placeholder').objects.filter(title_id__isnull=True):
        context_extras[pc.slot] = mark_safe(pc.body)

    return context_extras
