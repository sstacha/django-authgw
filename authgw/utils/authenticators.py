"""
Utilities for working with data from the request to test front end pages
NOTE: this should only be used for local testing and use an LDAP authenticator instead when deployed; still working
    this through
NOTE: this whole front end authentication thing is very alpha.  I am thinking development sets headers/cookies through
    login but deploy only sets by proxy header or actual login service; not really sure at this point.  I may delete
    this and just use the django admin backend authenticator stuff.
    TODO: think this though
"""
from django.http import HttpRequest


# -------- primitive conversions --------
def to_int(value, default=0, none_to_default=True):
    """
    Convert <value> to int.  Will always return integer or none instead of throwing exception
    @param value: value to be converted
    @param default: default value to use if none or error (defaults to 0 but set to None to have nulls in db)
    @param none_to_default: preserve a None value or convert to the default; Note: still checks default value afterwards
    @return: integer value or default or None depending on options
    """
    if value is None and not none_to_default:
        return None
    if value is None:
        value = default
    try:
        return int(value)
    except Exception:
        # if any exception occurs lets print to screen and then return the supplied default value
        print(f"WARNING: exception converting <{str(value)}> to int; returning default value: {str(default)}!")
        return default


class RequestAuthenticator:
    """
    Encapsulates the data and methods for interrogating a visitors authentication or authorization
    Defualt request authenticator looks for django user in request
    """
    def __init__(self, request: HttpRequest = None):
        self.request = request
        self.ip = None
        self.user = None
        # consider these things under a user request object?
        self.first_name = None
        self.last_name = None
        self.username = None
        self.email = None
        self.init()
        self.init_ip()

    def init(self):
        # initialize our required properties
        if self.request:
            self.user = getattr(self.request, 'user', None)
            if self.user and not self.user.is_anonymous:
                self.first_name = getattr(self.user, 'first_name', None)
                self.last_name = getattr(self.user, 'last_name', None)
                self.email = getattr(self.user, 'email', None)
                self.username = getattr(self.user, 'username', None)

    def init_ip(self):
        if self.request:
            # by default we will use the META REMOTE_ADDR which works if not proxied
            self.ip = self.request.META.get('REMOTE_ADDR')

    def is_authenticated(self):
        """
        Determines if a user is logged in; currently based on cookies.  Ideally, this would check the auth server later
        @param self: the current auth object containing the needed properties from the request
        @return: True/False
        """
        return self.user is not None


class EmetaAuthenticator(RequestAuthenticator):
    def init(self):
        super().init()
        # initialize our new required properties
        self.auth_cookie = None
        self.auth_id = 0
        self.crm_id = None
        if self.request:
            self.auth_cookie = self.request.COOKIES.get('ERIGHTS')
            self.auth_id = to_int(self.request.COOKIES.get('emeta_id'))
            self.crm_id = self.request.COOKIES.get('cpid')
            if not self.crm_id:
                self.crm_id = self.request.COOKIES.get('sm_constitid')
            self.first_name = self.request.COOKIES.get('first_name')
            self.last_name = self.request.COOKIES.get('last_name')
            self.username = f'[{self.crm_id}] '
            if self.first_name and len(self.first_name) > 0:
                self.username += self.first_name.lower().strip()[:1]
            if self.last_name and len(self.last_name) > 0:
                self.username += self.last_name.lower().strip()
            self.email = self.request.COOKIES.get('email')

    def init_ip(self):
        if self.request:
            # set the ip address; start with proxy which sets http-x-real-ip header
            self.ip = self.request.META.get('HTTP_X_REAL_IP')
            if not self.ip:
                # next try nginx local webserver which uses http-x-forwared-for
                self.ip = self.request.META.get('HTTP_X_FORWARDED_FOR')
                if not self.ip:
                    # last use the normal remote_addr for localhost testing
                    super().init_ip()

    def is_authenticated(self):
        """
        Emeta authentication depends on the cookies being set instead of the user existing and not being anon user
        """
        return self.auth_cookie and self.auth_id and self.crm_id
