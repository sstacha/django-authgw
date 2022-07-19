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

First, and foremost, I am building this application to be included in all my projects that need to connect to our Active Directory instance for staff to use the admin screens.  My vision is that this may also grow to be able to be used externally by users as well.  I am thinking users can register in the same django users/groups table for small apps or sites.  This could be extended to allow connecting to a centralized user store at the proxy across all applications.  And could be extended further by adding a feature to connect to something like keycloak using OpenID Connect and JWT's.  The goal is to pip install this app into any project, add some configuration settings, and have it just work.  I am shooting for as little user/group administration at the application or project level as possible.

## Use Cases
* Developer wants to have a SQLite database and use manage.py to create users/superusers (for test scripts)
* Developer wants to connect to Active Directory locally if on VPN for debugging just like a deployed server
* Staff attempts to log into the admin, does not exist in Django and is configured to use Active Directory Backend
    * Backend should create user; sync any groups
* Staff should authenticate against AD for passwords and fall back to Django so one config can do all the above
* Developer needs to set cookies or headers to simulate a login for testing; maybe... still thinking through this one

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
Migrate to make sure database is populated and updated
```shell script
./manage.py migrate
```
Run django and login using your active directory username and password.  User will be created if it does not exist.

NOTE: User must be placed in an ActiveDirectory group called DJANGO_SUPERUSERS to have the superuser flag set.

NOTE: password is set to a random uuid during creation; you will need to reset it on your local machine to fall back to using the django login and password in the local database.
