import hashlib
from django.conf import settings
from django.core.cache import cache as django_cache



KEY_PREFIX = '%(db)s:%(model)s'

KEY = KEY_PREFIX + ':%(uid)d:%(method)s:%(args)r'

CACHABLE_METHODS = ('search', 'read', 'fields_get', 'fields_view_get',
                    'get_context', 'get')

RESET_CACHE_METHODS = ('write', 'create')


class Cacher(object):

    index_templ = 'INDEX_FOR:%(uid)s%(db)s:%(model)s'

    def get_key_by_params(self, params):
        return hashlib.sha1(KEY % params).hexdigest()

    def is_cachable(self, params):
        if not getattr(settings, 'OPENERP_CALL_CACHE', False):
            return False
        if getattr(settings, 'OPENERP_CONDITIONAL_RESET_CACHE', False) and \
                                                 params['model'] == 'cache.log':
            return False
        method = params.get('method')
        if method not in CACHABLE_METHODS:
            return False
        # TODO: checker by model
        return True

    def delete(self, key):
        return django_cache.delete(key)

    def get(self, key=None, params=None):
        if key is None:
            key = self.get_key_by_params(params)
        return django_cache.get(key)

    def del_cache(self, params):
        index_key = self.index_templ % params
        index_set = django_cache.get(index_key, set())
        django_cache.delete_many(index_set)
        django_cache.delete(index_key)

    def set_index(self, params, key):
        index_key = self.index_templ % params
        index_set = django_cache.get(index_key, set())
        index_set.add(key)
        django_cache.set(index_key, index_set)

    def set(self, key=None, value=None, params=None):
        if key is None:
            if not self.is_cachable(params):
                return
            key = self.get_key_by_params(kwargs)
        if params:
            self.set_index(params, key)
        return django_cache.set(key, value)

    def call(self, func, params):
        _call = lambda: func(params['db'], params['uid'], params['password'],
                               params['model'], params['method'],
                               *params['args'])
        if not self.is_cachable(params):
            res = _call()
            if res and getattr(settings, 'OPENERP_CALL_CACHE', False) \
                   and params['method'] in RESET_CACHE_METHODS:
                self.del_cache(params)
            return res, False
        key = self.get_key_by_params(params)
        cache_res = self.get(key)
        if cache_res is None:
            res = _call()
            self.set(key, res, params)
            return res, False
        return cache_res, True

    def get_last_cache_reset(self, db):
        res = django_cache.get('OpenERP-LM-%s' % db)
        return res

    def set_last_cache_reset(self, db, dt):
        django_cache.set('OpenERP-LM-%s' % db, dt)

cache = Cacher()
