from functools import partial

from zope.interface import implementer

from pyramid.compat import (
    bytes_,
    urlparse,
    )
from pyramid.exceptions import (
    BadCSRFOrigin,
    BadCSRFToken,
)
from pyramid.interfaces import ICSRF
from pyramid.settings import aslist
from pyramid.util import (
    is_same_domain,
    strings_differ,
)


@implementer(ICSRF)
class SessionCSRF(object):
    """ The default CSRF implementation, which mimics the behavior from older
    versions of Python. The ``new_csrf_token`` and ``get_csrf_token`` methods
    are indirected to the underlying session implementation.

    Note that using this CSRF implementation requires that
    a :term:`session factory` is configured.

    .. versionadded :: 1.8a1
    """
    def new_csrf_token(self, request):
        """ Sets a new CSRF token into the session and returns it. """
        return request.session.new_csrf_token()

    def get_csrf_token(self, request):
        """ Returns the currently active CSRF token from the session, generating
        a new one if needed."""
        return request.session.get_csrf_token()


def csrf_token_template_global(event):
    request = event.get('request', None)
    try:
        registry = request.registry
    except AttributeError:
        return
    else:
        csrf = registry.queryUtility(ICSRF)
        if csrf is not None:
            event['get_csrf_token'] = partial(csrf.get_csrf_token, request)


def get_csrf_token(request):
    """ Get the currently active CSRF token for the request passed, generating
    a new one using ``new_csrf_token(request)`` if one does not exist. This
    calls the equivalent method in the chosen CSRF protection implementation.

    .. versionadded :: 1.8a1
    """
    registry = request.registry
    csrf = registry.queryUtility(ICSRF)
    if csrf is not None:
        return csrf.get_csrf_token(request)


def new_csrf_token(request):
    """ Generate a new CSRF token for the request passed and persist it in an
    implementation defined manner. This calls the equivalent method in the
    chosen CSRF protection implementation.

    .. versionadded :: 1.8a1
    """
    registry = request.registry
    csrf = registry.queryUtility(ICSRF)
    if csrf is not None:
        return csrf.new_csrf_token(request)


def check_csrf_token(request,
                     token='csrf_token',
                     header='X-CSRF-Token',
                     raises=True):
    """ Check the CSRF token returned by the :meth:`pyramid.interfaces.ICSRF`
    implementation against the value in ``request.POST.get(token)`` (if a POST
    request) or ``request.headers.get(header)``. If a ``token`` keyword is not
    supplied to this function, the string ``csrf_token`` will be used to look
    up the token in ``request.POST``. If a ``header`` keyword is not supplied
    to this function, the string ``X-CSRF-Token`` will be used to look up the
    token in ``request.headers``.

    If the value supplied by post or by header doesn't match the value supplied
    by ``impl.get_csrf_token()`` (where ``impl`` is an implementation of
    :meth:`pyramid.interfaces.ICSRF`), and ``raises`` is ``True``, this
    function will raise an :exc:`pyramid.exceptions.BadCSRFToken` exception. If
    the values differ and ``raises`` is ``False``, this function will return
    ``False``.  If the CSRF check is successful, this function will return
    ``True`` unconditionally.

    See :ref:`auto_csrf_checking` for information about how to secure your
    application automatically against CSRF attacks.

    .. versionadded:: 1.4a2

    .. versionchanged:: 1.7a1
       A CSRF token passed in the query string of the request is no longer
       considered valid. It must be passed in either the request body or
       a header.

    .. versionchanged:: 1.8a1
       Moved from pyramid.session to pyramid.csrf
    """
    supplied_token = ""
    # If this is a POST/PUT/etc request, then we'll check the body to see if it
    # has a token. We explicitly use request.POST here because CSRF tokens
    # should never appear in an URL as doing so is a security issue. We also
    # explicitly check for request.POST here as we do not support sending form
    # encoded data over anything but a request.POST.
    if token is not None:
        supplied_token = request.POST.get(token, "")

    # If we were unable to locate a CSRF token in a request body, then we'll
    # check to see if there are any headers that have a value for us.
    if supplied_token == "" and header is not None:
        supplied_token = request.headers.get(header, "")

    impl = request.registry.getUtility(ICSRF)
    expected_token = impl.get_csrf_token(request)
    if strings_differ(bytes_(expected_token), bytes_(supplied_token)):
        if raises:
            raise BadCSRFToken('check_csrf_token(): Invalid token')
        return False
    return True


def check_csrf_origin(request, trusted_origins=None, raises=True):
    """
    Check the Origin of the request to see if it is a cross site request or
    not.

    If the value supplied by the Origin or Referer header isn't one of the
    trusted origins and ``raises`` is ``True``, this function will raise a
    :exc:`pyramid.exceptions.BadCSRFOrigin` exception but if ``raises`` is
    ``False`` this function will return ``False`` instead. If the CSRF origin
    checks are successful this function will return ``True`` unconditionally.

    Additional trusted origins may be added by passing a list of domain (and
    ports if nonstandard like `['example.com', 'dev.example.com:8080']`) in
    with the ``trusted_origins`` parameter. If ``trusted_origins`` is ``None``
    (the default) this list of additional domains will be pulled from the
    ``pyramid.csrf_trusted_origins`` setting.

    Note that this function will do nothing if request.scheme is not https.

    .. versionadded:: 1.7

    .. versionchanged:: 1.8a1
       Moved from pyramid.session to pyramid.csrf
    """
    def _fail(reason):
        if raises:
            raise BadCSRFOrigin(reason)
        else:
            return False

    if request.scheme == "https":
        # Suppose user visits http://example.com/
        # An active network attacker (man-in-the-middle, MITM) sends a
        # POST form that targets https://example.com/detonate-bomb/ and
        # submits it via JavaScript.
        #
        # The attacker will need to provide a CSRF cookie and token, but
        # that's no problem for a MITM when we cannot make any assumptions
        # about what kind of session storage is being used. So the MITM can
        # circumvent the CSRF protection. This is true for any HTTP connection,
        # but anyone using HTTPS expects better! For this reason, for
        # https://example.com/ we need additional protection that treats
        # http://example.com/ as completely untrusted. Under HTTPS,
        # Barth et al. found that the Referer header is missing for
        # same-domain requests in only about 0.2% of cases or less, so
        # we can use strict Referer checking.

        # Determine the origin of this request
        origin = request.headers.get("Origin")
        if origin is None:
            origin = request.referrer

        # Fail if we were not able to locate an origin at all
        if not origin:
            return _fail("Origin checking failed - no Origin or Referer.")

        # Parse our origin so we we can extract the required information from
        # it.
        originp = urlparse.urlparse(origin)

        # Ensure that our Referer is also secure.
        if originp.scheme != "https":
            return _fail(
                "Referer checking failed - Referer is insecure while host is "
                "secure."
            )

        # Determine which origins we trust, which by default will include the
        # current origin.
        if trusted_origins is None:
            trusted_origins = aslist(
                request.registry.settings.get(
                    "pyramid.csrf_trusted_origins", [])
            )

        if request.host_port not in set(["80", "443"]):
            trusted_origins.append("{0.domain}:{0.host_port}".format(request))
        else:
            trusted_origins.append(request.domain)

        # Actually check to see if the request's origin matches any of our
        # trusted origins.
        if not any(is_same_domain(originp.netloc, host)
                   for host in trusted_origins):
            reason = (
                "Referer checking failed - {0} does not match any trusted "
                "origins."
            )
            return _fail(reason.format(origin))

    return True
