import xmlrpclib
from django.utils.encoding import force_unicode
from djoe.base.backends.base import Connection, OpenERPException


class XMLRPCConnection(Connection):

    def proxy(self, service):
        cache_attr = '_%s_proxy' % service
        cache_proxy = getattr(self, cache_attr, None)
        if cache_proxy is None:
            cache_proxy = xmlrpclib.ServerProxy( \
                'http://%(host)s:%(port)d/xmlrpc/%(serv)s' % \
                dict(host=self.host, port=self.port, serv=service),
                allow_none=True)
        setattr(self, cache_attr, cache_proxy)
        return cache_proxy

    def objects(self, db, user_id, password, model, meth, *args, **kwargs):
        try:
            result = self.proxy('object').execute(db, user_id,
                                   password, model, meth, *args, **kwargs)
        except xmlrpclib.Fault, e:
            raise OpenERPException(force_unicode(e))
        return result
