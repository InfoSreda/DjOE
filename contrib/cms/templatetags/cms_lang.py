from django.template.base import Node, NodeList, Template, Context, Variable
from django.template.base import get_library, Library, InvalidTemplateLibrary
from django.template.smartif import IfParser, Literal
from django.conf import settings
from django.utils.encoding import smart_str, smart_unicode
from django.utils.safestring import mark_safe
from django.template.defaulttags import url as django_url
from django.utils import translation

register = Library()

class UrlLangNode(Node):
    def __init__(self, urlnode, lang):
        self.urlnode = urlnode
        self.lang = lang

    def render(self, context):
        url = self.urlnode.render(context)
        return '/%s%s' %( self.lang, url )


def url_lang(parser, token):
    url = django_url(parser, token)
    lang = translation.get_language()[:2]
    if lang != settings.LANGUAGE_CODE[:2]:
        urlnode = UrlLangNode(url, lang)
        return urlnode
    return url

register.tag(url_lang)
