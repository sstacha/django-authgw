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

```
Add other settings based on your use case
### Enable settings to connect to Active Directory
```python

```
