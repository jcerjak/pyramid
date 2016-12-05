What's New in Pyramid 1.8
=========================

This article explains the new features in :app:`Pyramid` version 1.8 as
compared to its predecessor, :app:`Pyramid` 1.7. It also documents backwards
incompatibilities between the two versions and deprecations added to
:app:`Pyramid` 1.8, as well as software dependency changes and notable
documentation additions.

Backwards Incompatibilities
---------------------------

- None yet

Feature Additions
-----------------

- A new CSRF implementation, :class:`pyramid.csrf.SessionCSRF` has been added,
  which deleagates all CSRF generation to the current session, following the old
  API for this.

- A ``get_csrf_token()`` method is now available in template global scope, to
  make it easy for template developers to get the current CSRF token without
  adding it to Python code.

Deprecations
------------

- Retrieving CSRF token from the session has been deprecated, in favor of
  equivalent methods in :mod:`pyramid.csrf`.

Scaffolding Enhancements
------------------------

- None yet

Documentation Enhancements
--------------------------

- None yet