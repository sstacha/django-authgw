"""
The login application is an interface to allow other apps or URLs to be protected
NOTES:
The main purpose is to allow for connecting locally to a faux form to set cookies that can be used without having
the full login stack on a developer laptop.  In addition, redirecting to where needed by data configuration.
Ex: app can call /login/ or /logout/ which then takes care of logging in/out for an implementation.
Might extend to allow logging into django proper or other external (ldap) system for real
Might extend to allow adaptive login
Might extend to be callable by nginx; generally allow growing to external system
Needs to be very flexible to allow for different types of authentication; look into github or google auth passthrough
Consider a middleware with utility library as well for use in views and such or add to request
Create login django user if not there for admin?
SEE README.md for up-to-date list of features ond description
"""
from django.apps import AppConfig


class AuthgwConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'authgw'
