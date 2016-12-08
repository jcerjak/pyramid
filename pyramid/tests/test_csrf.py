import unittest

from pyramid.config import Configurator
from pyramid.csrf import SessionCSRF, get_csrf_token, new_csrf_token
from pyramid.events import BeforeRender
from pyramid.interfaces import ICSRFPolicy
from pyramid.tests.test_view import BaseTest as ViewBaseTest


class CSRFTokenTests(ViewBaseTest, unittest.TestCase):
    class DummyCSRF(object):
        def new_csrf_token(self, request):
            return 'e5e9e30a08b34ff9842ff7d2b958c14b'

        def get_csrf_token(self, request):
            return '02821185e4c94269bdc38e6eeae0a2f8'

    def test_csrf_token_passed_to_template(self):
        config = Configurator()
        config.set_default_csrf_options(implementation=self.DummyCSRF)
        config.commit()

        request = self._makeRequest()
        request.registry = config.registry

        before = BeforeRender({'request': request}, {})
        config.registry.notify(before)
        self.assertIn('get_csrf_token', before)
        self.assertEqual(
            before['get_csrf_token'](),
            '02821185e4c94269bdc38e6eeae0a2f8'
        )

    def test_simple_api_for_tokens_from_python(self):
        config = Configurator()
        config.set_default_csrf_options(implementation=self.DummyCSRF)
        config.commit()

        request = self._makeRequest()
        request.registry = config.registry
        self.assertEqual(
            get_csrf_token(request),
            '02821185e4c94269bdc38e6eeae0a2f8'
        )
        self.assertEqual(
            new_csrf_token(request),
            'e5e9e30a08b34ff9842ff7d2b958c14b'
        )


class SessionCSRFTests(unittest.TestCase):
    class MockSession(object):
        def new_csrf_token(self):
            return 'e5e9e30a08b34ff9842ff7d2b958c14b'

        def get_csrf_token(self):
            return '02821185e4c94269bdc38e6eeae0a2f8'

    def test_session_csrf_implementation_delegates_to_session(self):
        config = Configurator()
        config.set_default_csrf_options(implementation=SessionCSRF)
        config.commit()

        request = DummyRequest(config.registry, self.MockSession())
        self.assertEqual(
            config.registry.getUtility(ICSRFPolicy).get_csrf_token(request),
            '02821185e4c94269bdc38e6eeae0a2f8'
        )
        self.assertEqual(
            config.registry.getUtility(ICSRFPolicy).new_csrf_token(request),
            'e5e9e30a08b34ff9842ff7d2b958c14b'
        )


class DummyRequest(object):
    registry = None
    session = None

    def __init__(self, registry, session):
        self.registry = registry
        self.session = session
