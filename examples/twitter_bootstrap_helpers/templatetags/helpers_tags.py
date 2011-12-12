from django import template
from django.template.defaulttags import url


register = template.Library()

# TODO: It's better to use inheritance than decorating here.
def markup(func, nodelist, bullseye):
    def wrapper(*args, **kwargs):
        context = args[0]
        request = context['request']
        path = request.path
        url = func(*args, **kwargs)
        is_active = path == url if bullseye else path.startswith(url)
        c = template.Context({
            'url': url,
            'is_active': is_active,
            'title': nodelist.render(context)
        })
        t = template.loader.get_template('_menuitem.html')
        return t.render(c)
    return wrapper

def menuitem(parser, token):
    bullseye = '_bullseye'
    head, sep, tail = token.contents.partition(bullseye)
    token.contents = ' '.join([head.rstrip(), tail.lstrip()])
    nodelist = parser.parse(('endmenuitem',))
    parser.delete_first_token()
    node = url(parser, token)
    node.render = markup(node.render, nodelist, bool(sep))
    return node

menuitem = register.tag(menuitem)
