# -*- coding: utf-8 -*-
import base64
import mimetypes
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404
from django.shortcuts import get_list_or_404
from django.shortcuts import render_to_response, redirect
from djoe.base.backends import oe_session
from django import forms
from django.template import RequestContext
from django.conf import settings
from django.utils.safestring import mark_safe


DEFAULT_MIMETYPE = 'application/octet-stream'

def cms_media(request, path):
    file_name = path.rsplit('/', 1)[-1]
    mime_type = mimetypes.guess_type(file_name)[0]
    if mime_type is None:
        mime_type = DEFAULT_MIMETYPE
    resp = HttpResponse(mimetype=mime_type)
    data = oe_session.objects('cms.media.file', 'get_data', path)
    resp.write(base64.decodestring(data))
    return resp


def cms(request, path):
    host = request.get_host()
    if path.endswith('/'):
        path = path[:-1]
    w_path = path.split('/', 1)
    if len(w_path[0]) == 2:
        if len(w_path) == 1:
            path = ''
        else:
            path = '%s' % w_path[1]

    site = get_object_or_404(oe_session.get_model('cms.site'), host=host)
    query = {'page_id__published':True,
             'page_id__site_id__id':site.pk}
    if request.LANGUAGE_ID:
        query['language_id'] = request.LANGUAGE_ID
    else:
        query['language_id__code'] = settings.LANGUAGE_CODE

    Title = oe_session.get_model('cms.title')
    full_path = request.get_full_path()[1:]
    if full_path != path:
        query['old_path'] = full_path
    else:
        query['path'] = path
    try:
        title = Title.objects.get(**query)
    except Title.DoesNotExist:
        if 'path' in query:
            raise Http404
        del query['old_path']
        query['path'] = path
        try:
            title = Title.objects.get(**query)
        except Title.DoesNotExist:
            raise Http404
    else:
        if 'old_path' in query:
            return redirect(cms, path=title.path, permanent=True)

    if title.publication_date and title.publication_date > now:
        raise Http404
    if title.publication_end_date and \
               title.publication_end_date < now:
        raise Http404

    ctx = {
        'site_name': site.name,
        'title': title,
        'is_catalogue': path.startswith('catalogue')
        }
    for pc in oe_session.get_model('cms.placeholder').objects.filter(title_id=title):
        ctx[pc.slot_id.name] = mark_safe(pc.body)

    return render_to_response('cms/%s' % title.template_name, ctx,
                              context_instance=RequestContext(request))

