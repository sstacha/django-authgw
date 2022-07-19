# django-authgw
django-authgw is a django application for developers who build, manage and maintain websites.  This app is intended to support various methods of authenticating and authorizing into a Django based site or application based on URL patterns.

[ubercode.io: authgw](https://www.ubercode.io/products/#docrootcms_overview)
> Because the code matters

## Dependencies
* Python >= 3.8
* django >= 3
* ldap3

## Idea
Authentication and authorization is complicated and there are several use cases where it would be nice to have a configurable application that can work differently based on the need.

## Use Cases
* Developer wants to have a SQLite database and use manage.py to create users/superusers
* Developer wants to test connecting to Active Directory if on VPN first
* Staff attempts to log into the admin but does not exist in Django but tied to Active Directory Backend
    * Backend should create user; sync any groups
* Staff should authenticate against AD for passwords and fall back to Django
* Developer needs to set cookies or headers to simulate a login for testing

## Install Instructions
Simply add django-authgw to your requirements.txt or pip install the app
```shell script
pip install django-authgw
```
Add 'authgw' to the INSTALLED_APPS list in your settings.py
```python
INSTALLED_APPS = [
   ...,
   'authgw',
]
```
Add other settings based on your use case
### Enable settings to connect to Active Directory
```python
# LDAP/AD AUTHENTICATION
# ----
# NOTE: using default AD auth (NTLM)
LDAP_HOST = 'myldapdirectory.example.org'
AD_DOMAIN = 'MYDOMAIN'
AD_USER_ID_PREFIX = 'u:'
LDAP_USER_SEARCH_DN = "ou=OFFICES,dc=example,dc=org"
LDAP_USER_SEARCH_QUERY = "(&(objectclass=person)(sAMAccountName={}))"
LDAP_AUTHENTICATED_GROUPS = ['Everyone']
# NOTE: create the Everyone group in Django and assign permissions you want everyone to have when the authenticate
#  Users will automatically be added to the group if they aren't there after they authenticate; Users will also 
#  automatically be added to any matching LDAP group found in the Django application.
# NOTE: by default, users will have the superuser flag set on creation only if they are in a DJANGO_SUPERUSERS group
#  in ActiveDirectory; this can be changed by overriding the method on the authgw.utils.ldap3.LdapUser object and 
#  then overriding the authgw.utils.ldap3.ActiveDirectoryAuthenticator.get_ldap_user_instance() method

AUTHENTICATION_BACKENDS = ['authgw.utils.ldap3.LdapBackend', 'django.contrib.auth.backends.ModelBackend']

```
Other variables that might be needed if defaults don't work for you
```python
LDAP_AUTHENTICATION='AD' # change to 'LDAP' to use the LdapAuthenticator instead of the ActiveDirectoryAuthenticator
# NOTE: LDAP authentication requires an extra bind so AD is preferred if you can use it
LDAP_PORT=None # if specified in LDAP_HOST that is used, otherwise if set this, otherwise defaults to ldap3 constructor default
LDAP_USE_SSL=None # if specifed in LDAP_HOST that is used, otherwise if set this, otherwise defults to ldap3 constructor default
AD_BIND_USER=None # need if searching instead of authenticating someone
AD_BIND_PASSWORD=None # need if searching instead of authenticating someone
LDAP_BIND_DN=None # needed if using LDAP_AUTHENTICATION='LDAP'; ex: "CN=First Last,OU=STAFF,OU=PEOPLE,OU=ASIA,OU=OFFICES,DC=example,DC=org"
LDAP_BIND_PASSWORD=None # needed if using LDAP_AUTHENTICATION='LDAP'
```
