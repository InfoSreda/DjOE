"""
from docutils.core import publish_cmdline
from djoe.base.backends import oe_session


def wiki_page(request, object_id):
    #wiki_page = oe_session.get_model('wiki.wiki').objects.get(pk=object_id)
    #print 222222222222, publish_cmdline(writer_name='html', description=wiki_page.text_area)

    return object_detail, {
            'queryset': oe_session.get_model('wiki.wiki').objects.all(),
            'template_name': 'wiki/detail.html',
            'template_object_name': 'wiki_page'
            }, name='wiki_page')
"""
