import socket
import cPickle
import sys

from django.utils.encoding import force_unicode
from djoe.base.backends.base import Connection, OpenERPException


TIMEOUT = 120

class SocketRecieveError(Exception):
    pass


class NetRPCProxy(object):

    def __init__(self, host, port, service='object'):
        self.host = host
        self.port = port
        self.service = service
        self.init_socket()

    def init_socket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(TIMEOUT)
        self.connected = False
        
    def connect(self):
        self.socket.connect((self.host, self.port))
        self.connected = True

    def disconnect(self):
        try:
            if sys.platform != 'darwin':
                self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
        except:
            pass

    def send(self, msg, exception=False, traceback=None):
        pickled_msg = cPickle.dumps([msg, traceback])
        self.socket.sendall('%8d%d%s' % (len(pickled_msg),
                                         int(bool(exception)),
                                         pickled_msg))

    def _chunked_read(self, size):
        buf = ''
        cursor = 0
        while cursor < size:
            chunk = self.socket.recv(size - cursor)
            if chunk == '':
                raise SocketRecieveError()
            buf += chunk
            cursor += len(chunk)
        return buf

    def receive(self):
        size = int(self._chunked_read(8))
        exc = bool(int(self._chunked_read(1)))
        res = cPickle.loads(self._chunked_read(size))

        if isinstance(res[0], Exception):
            if exc:
                raise OpenERPException(u'\n'.join((force_unicode(r) for r in res)))
            raise res[0]
        return res[0]

    def __getattr__(self, name):
        if name.startswith('__') or name in dir(self):
            return super(NetRPCProxy, self).__getattr__(name)
        def meth(*args):
            args = (self.service, name,) + args
            while True:
                if not self.connected:
                    self.connect()
                try:
                    self.send(args)
                    res = self.receive()
                except (SocketRecieveError, socket.error), exc:
                    self.disconnect()
                    self.init_socket()
                    continue
                break
            self.disconnect()                    
            return res
        return meth


class NetRPCConnection(Connection):

    def __init__(self, *args, **kwargs):
        super(NetRPCConnection, self).__init__(*args, **kwargs)
        self._proxy = NetRPCProxy(self.host, self.port)

    def proxy(self, service):
        self._proxy.service = service
        return self._proxy

    def objects(self, db, user_id, password, model, meth, *args, **kwargs):
        result = self.proxy('object').execute(db, user_id,
                                   password, model, meth, *args, **kwargs)
        return result
