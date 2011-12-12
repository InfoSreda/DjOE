from django.utils.cache import patch_vary_headers
from django.utils import translation
from djoe.base.backends import oe_session
from django.conf import settings


class LocaleMiddleware(object):
    """
    Copy of django.locale middleware
    """

    def _get_lang_code(self, request):
        full_path = request.get_full_path()
        w_path = full_path[1:].split('/', 1)
        request.PATH_LANG = ''
        request.PATH_WITHOUT_LANG = ''
        language = settings.LANGUAGE_CODE
        request.LANGUAGE_ID = None

        if len(w_path[0]) == 2:
            try:
                lang = oe_session.get_model('res.lang').objects.get(iso_code=w_path[0])
            except:
                pass
            else:
                language = lang.code
                request.PATH_LANG = w_path[0]
                request.LANGUAGE_ID = lang.id
            if len(w_path) == 2:
                request.PATH_WITHOUT_LANG = w_path[1]
        else:
            request.PATH_WITHOUT_LANG = full_path
        if oe_session._default_context is None:
            oe_session._default_context = {}
        oe_session._default_context.update(lang=language)
        return language

    def process_request(self, request):
        language = self._get_lang_code(request)
        translation.activate(language)
        request.LANGUAGE_CODE = translation.get_language()

    def process_response(self, request, response):
        patch_vary_headers(response, ('Accept-Language',))
        if 'Content-Language' not in response:
            response['Content-Language'] = translation.get_language()
        translation.deactivate()
        return response
