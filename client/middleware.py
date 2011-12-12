from django.contrib import auth
from django.core.exceptions import ImproperlyConfigured


class OpenERPMiddleware(object):

    def process_request(self, request):
        if hasattr(request, 'user') and request.user:
            if isinstance(request.user, auth.models.AnonymousUser):
                return None
            from djoe.base.backends import oe_session, OpenERPSession
            assert isinstance(request.user, OpenERPSession), \
            'OpenERPMiddleware must be used with authbackend.OpenERPAuthBackend'
            oe_session.user_id = request.user.user_id
            oe_session.database = request.user.database
            oe_session.password = request.user.password
        return None
