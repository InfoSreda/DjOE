from django.conf import settings
from djoe.base.backends.xmlrpc import XMLRPCConnection, XMLRPCSConnection
from djoe.base.backends.netrpc import NetRPCConnection
from djoe.base.backends.base import OpenERPSession, OpenERPException

CONNECTIONS = {'xmlrpc': XMLRPCConnection,
               'netrpc': NetRPCConnection,
               'xmlrpcs': XMLRPCSConnection}

conn_cls = CONNECTIONS[settings.OPENERP_PROTOCOL]

connection = conn_cls(host=settings.OPENERP_HOST,
                      port=settings.OPENERP_PORT)

oe_session = OpenERPSession(connection)

if hasattr(settings, 'OPENERP_USER') and hasattr(settings, 'OPENERP_PASSWORD') \
       and hasattr(settings, 'OPENERP_DATABASE'):
    oe_session.login(settings.OPENERP_DATABASE, settings.OPENERP_USER,
                     settings.OPENERP_PASSWORD)
