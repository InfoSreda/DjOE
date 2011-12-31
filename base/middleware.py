import datetime
from djoe.base.backends import oe_session, OpenERPSession, OpenERPException
from django.conf import settings
from djoe.base.cache import cache
from djoe.base.utils import DATETIME_FORMATS

DEFAULT_DATE = '2010-01-01 00:00:00.000000'


class CacheResetMiddleware(object):

    def process_request(self, request):
        if not getattr(settings, 'OPENERP_CONDITIONAL_RESET_CACHE'):
            return None
        last_reset = cache.get_last_cache_reset(oe_session.database)
        if not last_reset:
            last_reset = DEFAULT_DATE

        now = datetime.datetime.now()
        
        if datetime.datetime.strptime(last_reset, DATETIME_FORMATS[1]) + \
             datetime.timedelta(seconds=settings.OPENERP_CACHE_CHECK_TIMEOUT) \
                                                     > now:
            return None
        ctx = oe_session.get_default_context()
        try:
            reset_cache_ids = oe_session.objects('cache.log', 'search',
                                [('last_modified', '>', last_reset)],
                                         0, None, 'last_modified', ctx)
        except OpenERPException, exc:
            if "Object cache.log doesn't exist" in unicode(exc):
                return
            raise
        last_mod = now.strftime(DATETIME_FORMATS[1])        
        if reset_cache_ids:
            last_modified_id = reset_cache_ids[-1]

            reset_data = {'db': oe_session.database, 'uid': oe_session.user_id}
            records = oe_session.objects('cache.log', 'read', reset_cache_ids,
                               ['last_modified', 'model_name'], ctx)
            for rec in records:
                reset_data['model'] = rec['model_name']
                cache.del_cache(reset_data)
                if last_modified_id == rec['id']:
                    last_mod = rec['last_modified']
        cache.set_last_cache_reset(oe_session.database, last_mod)
        return None
