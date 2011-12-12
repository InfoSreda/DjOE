from djoe.base.backends import OpenERPSession, connection


class OpenERPAuthBackend(object):
    """
    Authenticates openerp session
    """
    supports_object_permissions = False
    supports_anonymous_user = True

    def authenticate(self, username=None, password=None, database=None):
        session = OpenERPSession(connection=connection)
        session.login(database, username, password)
        if session.user_id:
            return session
        return None

    def get_user(self, user_id):
        '''
        user_id is dictionary {user_id, password, database}
        '''
        if not isinstance(user_id, dict) or not user_id.get('user_id'):
            return None
        session = OpenERPSession(connection=connection, **user_id)
        return session
