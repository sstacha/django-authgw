from django.shortcuts import render
from .utils.authenticators import RequestAuthenticator
from django.http import HttpResponseRedirect
from django.conf import settings
import uuid
import random
import urllib.parse


def get_qs(get_dict, fq_target=None, overridden=False, extra=None):
    # add all other params except _target to new qs
    qs = "?"
    first = True
    for key, value in get_dict.items():
        if key == '_target' and overridden:
            continue
        if first:
            first = False
        else:
            qs += '&'
        qs += f'{key}={value}'
    print(f'_target: {fq_target}')
    if fq_target and overridden:
        # append the target as ERIGHTS_TARGET instead
        if qs != "?":
            qs += '&'
        qs += f'ERIGHTS_TARGET={fq_target}'
    if extra:
        if qs != "?":
            qs += '&'
        qs += extra
    # last we might just have a ? if nothing above so test and remove
    if qs == "?":
        qs = ""
    return qs


def login(request):
    """
    route to login screen if we aren't authenticated otherwise continue on
    NOTE: this should be moved to middleware with a config for what should require login
    @param request: the request object
    @return: http response
    """
    # print(f'request hostname: {request.get_host()}')
    # print(f'request scheme: {request.scheme}')
    # for starters if we set a AUTHGW_LOGIN_URL param we redirect to it instead of showing a login form
    # NOTE: this should be set in a deployed env (dev, qa or prod)
    login_url_override = getattr(settings, 'AUTHGW_LOGIN_URL', None)
    if login_url_override:
        # look for a _target and replace with ERIGHTS_TARGET
        # NOTE: if we don't have a domain or request domain or its not the same as the login domain we should adjust
        _target = request.GET.get('_target')
        qs = request.META.get('QUERY_STRING')
        print(f'original qs: {qs}')
        if _target:
            _target = request.build_absolute_uri(_target)
            force_secure_scheme = getattr(settings, 'AUTHGW_FORCE_SECURE_SCHEME', None)
            if force_secure_scheme:
                if _target.lower().startswith('http:'):
                    _target = 'https:' + _target[5:]
        qs = get_qs(request.GET, _target, overridden=True)
        return HttpResponseRedirect(login_url_override + qs)

    # if we are on localhost and need to login we can use the faux login form to create cookies like our login does
    if request.method == 'POST':
        response = HttpResponseRedirect(request.POST.get('target', '/'))
        # tell the browser to set these cookies
        response.set_cookie('first_name', request.POST.get('first', ''), httponly=True)
        response.set_cookie('last_name', request.POST.get('last', ''), httponly=True)
        response.set_cookie('email', request.POST.get('email', ''), httponly=True)
        response.set_cookie('cpid', request.POST.get('cid', str(uuid.uuid4())[:7]), httponly=True)
        response.set_cookie('ERIGHTS', str(uuid.uuid4()), httponly=True)
        response.set_cookie('emeta_id', str(random.randint(1, 1000)), httponly=True)
        return response
    else:
        first = request.COOKIES.get('first_name', '')
        last = request.COOKIES.get('last_name', '')
        email = request.COOKIES.get('email', '')
        cid = request.COOKIES.get('cpid', '')
        # our target is expected to be a parameter since this is a mock form
        target = request.GET.get('_target', '')

        context = {'first': first, 'last': last, 'email': email, 'target': target, 'cid': cid}
        return render(request, 'authgw/login.html', context)


def logout(request):
    # our target is expected to be a parameter since this is a mock form
    # todo figure out if it is worth changing to a session variable later
    # https://qa.example.org/app/login/MyLoginServlet?command=logout
    _target = request.GET.get('_target', '/')
    login_url_override = getattr(settings, 'AUTHGW_LOGIN_URL', None)
    if login_url_override:
        _target = request.build_absolute_uri(_target)
        force_secure_scheme = getattr(settings, 'AUTHGW_FORCE_SECURE_SCHEME', None)
        if force_secure_scheme:
            if _target.lower().startswith('http:'):
                _target = 'https:' + _target[5:]
        qs = get_qs(request.GET, _target, overridden=True, extra="command=logout")
        response = HttpResponseRedirect(login_url_override + qs)
    else:
        qs = get_qs(request.GET)
        response = HttpResponseRedirect(_target + qs)
        # tell the browser to set these cookies
        response.set_cookie('first_name', '', httponly=True)
        response.set_cookie('last_name', '', httponly=True)
        response.set_cookie('email', '', httponly=True)
        response.set_cookie('cpid', '', httponly=True)
        response.set_cookie('ERIGHTS', '', httponly=True)
        response.set_cookie('emeta_id', '', httponly=True)
    return response
