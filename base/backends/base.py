import time
import logging
from django.conf import settings
from djoe.base.cache import cache

logger = logging.getLogger('openerp.rpc')


class Connection(object):

    def __init__(self, host, port, database=None):
        self.host = host
        self.port = port
        self.database = database


class OpenERPException(Exception):

    def as_html(self):
        from django.utils.html import escape
        lines = []
        for l in escape(unicode(self)).split('\\n'):
            if not l:
                continue
            if l[0] == ' ':
                if l.lstrip().startswith('File &quo'):
                    style='color:#444;margin:15px 0px 5px 0px;'
                else:
                    style='color:#494;'
            else:
                style='font-weight:bold;'
            l = l.replace(' ', '&nbsp;&nbsp;')
            lines.append('<p style="%s">%s</p>' % ( style, l))
        return u'<div>%s</div>' % u''.join(lines)


class OpenERPSession(object):

    def __init__(self, connection, user_id=None, database=None, password=None):
        self.connection = connection
        self.user_id = user_id
        self.queries = []
        self._cached_user = None
        self.database = database
        self.password = password
        self.model_pool = {}
        self._default_context = None

    def get_default_context(self):
        if self._default_context is None:
            self._default_context = self.objects('res.users', 'context_get')
        return self._default_context

    def execute(self, service, meth_name, *args):
        res = getattr(self.connection.proxy(service), meth_name)(*args)
        return res

    def login(self, database=None, username=None, password=None):
        self.database = database
        self.username = username
        self.password = password
        self.user_id = self.execute('common', 'login', database,
                                                             username, password)
        return self.user_id

    def objects(self, model, meth, *args, **kwargs):
        method = '`%s`.%s()' % (model, meth)
        if any([attr is None for attr in (self.user_id and self.database \
                                          and self.password)]):
            raise OpenERPException('User params not defined. Are you logged?')
        start = time.time()
        by_cache = False
        try:
            result, by_cache = cache.call(self.connection.objects,
                                          dict(db=self.database,
                                               uid=self.user_id,
                                               password=self.password,
                                               model=model,
                                               method=meth,
                                               args=args))
        except OpenERPException, e:
            logger.error(u'OpenERP %s raise: %r' % (method, e))
            raise
        finally:
            stop = time.time()
            duration = stop - start
            if settings.DEBUG and not by_cache:
                self.queries.append({
                    'method': method,
                    'args': repr(args),
                    'time': "%.3f" % duration
                })
            logger.debug('%s(%.3f) %s; args=%s' % ('CACHED:' if by_cache \
                                               else '', duration, method, args))
        return result

    def get_model(self, model_name, deep=0, fields=None,
                  exclude=None, all_oe_fields=None):
        from djoe.base.models import OpenERPModelFactory
        return OpenERPModelFactory(model_name, session=self, \
                 deep=deep, pool=self.model_pool).get_model(
            fields=fields, exclude=exclude,
            all_oe_fields=all_oe_fields)

    def get_user(self):
        if self._cached_user is None:
            self._cached_user = self.get_model('res.users').objects.\
                                get(id=self.user_id)
        return self._cached_user

    # django user methods
    def is_anonymous(self):
        return not bool(self.user_id)

    def is_authenticated(self):
        return  bool(self.user_id)


    @property
    def id(self):
        return dict(database=self.database, user_id=self.user_id,
                    password=self.password)

    @property
    def company_id(self):
        return self.get_user().company_id

    @property
    def name(self):
        return self.get_user().name

    @property
    def lang(self):
        return self.get_user().lang

    @property
    def action_id(self):
        return self.get_user().action_id

    @property
    def menu_id(self):
        return self.get_user().menu_id


    def save(self, **kwargs):
        # django auth
        return self
