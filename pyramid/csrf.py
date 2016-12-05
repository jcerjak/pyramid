from zope.interface import implementer
from pyramid.interfaces import ICSRF


@implementer(ICSRF)
class SessionCSRF(object):
    def new_csrf_token(self, request):
        return request.session.new_csrf_token()

    def get_csrf_token(self, request):
        return request.session.get_csrf_token()
