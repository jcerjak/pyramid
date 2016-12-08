import unittest

from zope.interface.interfaces import ComponentLookupError

from pyramid import testing
from pyramid.config import Configurator
from pyramid.events import BeforeRender


class Test_get_csrf_token(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def _callFUT(self, *args, **kwargs):
        from pyramid.csrf import get_csrf_token
        return get_csrf_token(*args, **kwargs)

    def test_no_csrf_utility_registered(self):
        request = testing.DummyRequest()

        with self.assertRaises(ComponentLookupError):
            self._callFUT(request)

    def test_success(self):
        self.config.set_default_csrf_options(implementation=DummyCSRF())
        request = testing.DummyRequest()

        csrf_token = self._callFUT(request)

        self.assertEquals(csrf_token, '02821185e4c94269bdc38e6eeae0a2f8')


class Test_new_csrf_token(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def _callFUT(self, *args, **kwargs):
        from pyramid.csrf import new_csrf_token
        return new_csrf_token(*args, **kwargs)

    def test_no_csrf_utility_registered(self):
        request = testing.DummyRequest()

        with self.assertRaises(ComponentLookupError):
            self._callFUT(request)

    def test_success(self):
        self.config.set_default_csrf_options(implementation=DummyCSRF())
        request = testing.DummyRequest()

        csrf_token = self._callFUT(request)

        self.assertEquals(csrf_token, 'e5e9e30a08b34ff9842ff7d2b958c14b')


class Test_csrf_token_template_global(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def _callFUT(self, *args, **kwargs):
        from pyramid.csrf import csrf_token_template_global
        return csrf_token_template_global(*args, **kwargs)

    def test_event_is_missing_request(self):
        event = BeforeRender({}, {})

        self._callFUT(event)

        self.assertNotIn('get_csrf_token', event)

    def test_request_is_missing_registry(self):
        request = DummyRequest(registry=None)
        del request.registry
        del request.__class__.registry
        event = BeforeRender({'request': request}, {})

        self._callFUT(event)

        self.assertNotIn('get_csrf_token', event)

    def test_csrf_utility_not_registered(self):
        request = testing.DummyRequest()
        event = BeforeRender({'request': request}, {})

        with self.assertRaises(ComponentLookupError):
            self._callFUT(event)

    def test_csrf_token_passed_to_template(self):
        config = Configurator()
        config.set_default_csrf_options(implementation=DummyCSRF())
        config.commit()

        request = testing.DummyRequest()
        request.registry = config.registry

        before = BeforeRender({'request': request}, {})
        config.registry.notify(before)

        self.assertIn('get_csrf_token', before)
        self.assertEqual(
            before['get_csrf_token'](),
            '02821185e4c94269bdc38e6eeae0a2f8'
        )


class SessionCSRFTests(unittest.TestCase):
    class MockSession(object):
        def new_csrf_token(self):
            return 'e5e9e30a08b34ff9842ff7d2b958c14b'

        def get_csrf_token(self):
            return '02821185e4c94269bdc38e6eeae0a2f8'

    def test_session_csrf_implementation_delegates_to_session(self):
        from pyramid.csrf import SessionCSRF
        from pyramid.interfaces import ICSRFPolicy

        config = Configurator()
        config.set_default_csrf_options(implementation=SessionCSRF())
        config.commit()

        request = DummyRequest(config.registry, session=self.MockSession())
        self.assertEqual(
            config.registry.getUtility(ICSRFPolicy).get_csrf_token(request),
            '02821185e4c94269bdc38e6eeae0a2f8'
        )
        self.assertEqual(
            config.registry.getUtility(ICSRFPolicy).new_csrf_token(request),
            'e5e9e30a08b34ff9842ff7d2b958c14b'
        )


class CookieCSRFTests(unittest.TestCase):
    def _makeOne(self):
        from pyramid.csrf import CookieCSRF
        return CookieCSRF()

    def _getICSRFPolicy(self):
        from pyramid.interfaces import ICSRFPolicy
        return ICSRFPolicy

    def test_get_cookie_csrf_with_no_existing_cookie_sets_cookies(self):
        config = Configurator()
        config.set_default_csrf_options(implementation=self._makeOne())
        config.commit()

        response = MockResponse()
        request = DummyRequest(config.registry, response=response)
        policy = self._getICSRFPolicy()

        token = config.registry.getUtility(policy).get_csrf_token(request)
        self.assertEqual(
            response.called_args,
            ('csrf_token', token),
        )
        self.assertEqual(
            response.called_kwargs,
            {
                'secure': False,
                'httponly': False,
                'domain': None,
                'path': '/',
                'overwrite': True
            }
        )

    def test_existing_cookie_csrf_does_not_set_cookie(self):
        config = Configurator()
        config.set_default_csrf_options(implementation=self._makeOne())
        config.commit()

        response = MockResponse()
        request = DummyRequest(config.registry, response=response)
        request.cookies = {'csrf_token': 'e6f325fee5974f3da4315a8ccf4513d2'}
        policy = self._getICSRFPolicy()

        token = config.registry.getUtility(policy).get_csrf_token(request)
        self.assertEqual(
            token,
            'e6f325fee5974f3da4315a8ccf4513d2'
        )
        self.assertEqual(
            response.called_args,
            (),
        )
        self.assertEqual(
            response.called_kwargs,
            {}
        )

    def test_new_cookie_csrf_with_existing_cookie_sets_cookies(self):
        config = Configurator()
        config.set_default_csrf_options(implementation=self._makeOne())
        config.commit()

        response = MockResponse()
        request = DummyRequest(config.registry, response=response)
        request.cookies = {'csrf_token': 'e6f325fee5974f3da4315a8ccf4513d2'}
        policy = self._getICSRFPolicy()

        token = config.registry.getUtility(policy).new_csrf_token(request)
        self.assertEqual(
            response.called_args,
            ('csrf_token', token),
        )
        self.assertEqual(
            response.called_kwargs,
            {
                'secure': False,
                'httponly': False,
                'domain': None,
                'path': '/',
                'overwrite': True
            }
        )


class DummyRequest(object):
    registry = None
    session = None
    cookies = {}

    def __init__(self, registry, session=None, response=None):
        self.registry = registry
        self.session = session
        self.response = response

    def add_response_callback(self, callback):
        callback(self, self.response)


class MockResponse(object):
    def __init__(self):
        self.called_args = ()
        self.called_kwargs = {}

    def set_cookie(self, *args, **kwargs):
        self.called_args = args
        self.called_kwargs = kwargs
        return


class DummyCSRF(object):
    def new_csrf_token(self, request):
        return 'e5e9e30a08b34ff9842ff7d2b958c14b'

    def get_csrf_token(self, request):
        return '02821185e4c94269bdc38e6eeae0a2f8'
