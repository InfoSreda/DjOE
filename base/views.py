import mimetypes
import base64
from django.http import HttpResponse, Http404
from djoe.base.backends import oe_session


def media(request, model, object_id, field):
    if request.user and request.user.is_authenticated():
        session = request.user
    else:
        session = oe_session
    try:
        base64data = session.objects(model, 'read', [object_id],
                                     [field])[0][field]
    except:
        raise Http404
    if not isinstance(base64data, basestring):
        raise Http404
    data = base64.b64decode(base64data)

    resp = HttpResponse()
    # TODO: not hardcode content-type
    resp['Content-Type'] = 'image/jpg'

    resp.write(data)
    return resp
