import unittest

from pyramid.config import Configurator
from pyramid.csrf import SessionCSRF
from pyramid.interfaces import ICSRF
from pyramid.renderers import RendererHelper

class MockSession(object):
    def get_csrf_token(self):
        return '02821185e4c94269bdc38e6eeae0a2f8'


class SessionCSRFTests(unittest.TestCase):
    
    def test_session_csrf_implementation_delegates_to_session(self):
        config = Configurator()
        config.set_default_csrf_options(implementation=SessionCSRF)
        config.commit()

        request = DummyRequest(config.registry, MockSession())
        self.assertEqual(
            config.registry.getUtility(ICSRF).get_csrf_token(request),
            '02821185e4c94269bdc38e6eeae0a2f8'
        )


# helper = RendererHelper()
# helper.render_view(request, 'response', 'view', 'context')
        
class DummyRequest(object):
    registry = None
    session = None
    def __init__(self, registry, session):
        self.registry = registry
        self.session = session
