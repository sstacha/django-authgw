import uuid
from ldap3 import Connection
from ldap3 import Server
from ldap3 import ALL, NTLM
from ldap3.core.exceptions import LDAPBindError, LDAPConfigurationParameterError, LDAPException
from pprint import pprint as prettyprint

from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User, Group
from django.conf import settings


class LdapUser:
    dn = None
    cn = None
    gn = None               # givenName
    sn = None
    country_code = None     # c
    state_code = None       # st
    city = None             # l
    department = None
    email = None            # mail
    title = None
    manager_dn = None       # manager
    login = None            # sAMAccountName
    # authenticated is marked after binding successfully with provided password
    is_authenticated = False

    def __init__(self):
        self._groups = []
        self._groups_dn = []  # memberOf

    # NOTE: we want the groups to be set when we set the groups dn; creating a property
    @property
    def groups_dn(self):
        return self._groups_dn

    @groups_dn.setter
    def groups_dn(self, groups_dn_value: [str]):
        self._groups_dn = groups_dn_value
        self._groups = []
        # loop over each record in the groups_dn and parse to get just the group name
        for group_dn in groups_dn_value:
            # ex dn: CN=ProjectOnlineResources,OU=GROUPS,OU=ASIA,OU=OFFICES,DC=example,DC=org
            # grab everything before the first comma
            cn_part = str(group_dn)[:str(group_dn).index(',')].strip().upper()
            if cn_part.startswith('CN='):
                cn_part = cn_part[3:]
            self._groups.append(cn_part)

    @property
    def groups(self):
        return self._groups

    @property
    def office(self):
        # try and extract the office from the users dn or None
        if not self.dn:
            return None
        else:
            dn_parts = str(self.dn).split(',')
            # print(f'dn_parts: {dn_parts}')
            # look for the index of the OU=OFFICES
            # if found assume the previous one is the office for this user
            previous_ou = None
            for dn_part in dn_parts:
                if dn_part.startswith('OU='):
                    if str(dn_part).strip() == 'OU=OFFICES':
                        return previous_ou
                    previous_ou = dn_part[3:]
            # if we didn't return something at this point we don't have any matching OU=
            return None

    # HELPER METHODS THAT CAN BE OVERRIDDEN PER APP
    # we want to dynamically pull the is_superuser and allow overriding per app
    # by default is true if _groups contains 'DJANGO_SUPERUSERS'
    def is_superuser(self):
        return 'DJANGO_SUPERUSERS' in self._groups

    # by default is true if department exists and is 'IT' in AD
    def is_it(self):
        return self.department and self.department == 'IT'

    # by default is staff is true if OU=STAFF is in their dn record
    def is_staff(self):
        return self.dn and 'OU=STAFF,' in self.dn

    def load(self, ldap_data_dict):
        if ldap_data_dict:
            self.dn = ldap_data_dict.distinguishedName.value
            self.cn = ldap_data_dict.cn.value
            self.gn = ldap_data_dict.givenName.value
            self.sn = ldap_data_dict.sn.value
            self.email = ldap_data_dict.mail.value
            self.country_code = ldap_data_dict.c.value
            self.state_code = ldap_data_dict.st.value
            self.city = ldap_data_dict.l.value
            self.department = ldap_data_dict.department.value
            self.title = ldap_data_dict.title.value
            self.login = ldap_data_dict.sAMAccountName.value
            self.manager_dn = ldap_data_dict.manager.value
            self.groups_dn = ldap_data_dict.memberOf.value

    def pprint(self):
        prettyprint(vars(self))

    def __str__(self):
        return str(vars(self))


# trying generic LDAP authentication
class LdapAuthenticator:
    """
    LdapAuthenticator will utilise basic LDAP connection for binding and searching; must know DN for bind user and
        or user logging in.  This can work for deployed machines using a bind user, however, ActiveDirectory is
        better generally since it is based on the login which we always know when a user tries to log in.
    """

    def __init__(self, host: str = None, bind_dn: str = None, bind_password: str = None, user_search_dn: str = None,
                 user_search_query: str = None):
        self.host = host or getattr(settings, 'LDAP_HOST', None)
        self.user_search_dn = user_search_dn or getattr(settings, 'LDAP_USER_SEARCH_DN', None)
        self.user_search_query = user_search_query or getattr(settings, 'LDAP_USER_SEARCH_QUERY', None)
        self.bind_user = bind_dn or getattr(settings, 'LDAP_BIND_DN', None)
        self.bind_password = bind_password or getattr(settings, 'LDAP_BIND_PASSWORD', None)

    def authenticate(self, login: str, password: str) -> LdapUser:
        return self.get_ldap_user(login, password)

    def get_ldap3_server(self):
        """
        making a function so can be overridden if fine grained control is needed
        :return: ldap3 server instance
        """
        port = getattr(settings, 'LDAP_PORT', None)
        ssl = getattr(settings, 'LDAP_USE_SSL', True)
        if port:
            return Server(self.host, port=port, use_ssl=ssl, get_info=ALL)
        return Server(self.host, use_ssl=ssl, get_info=ALL)

    @staticmethod
    def get_ldap_user_instance():
        return LdapUser()

    def get_ldap_user(self, login: str, password: str = None) -> LdapUser:
        # validate our settings to use for connecting
        # self.host = 'myldapserver.example.org'
        if not self.host:
            raise LDAPConfigurationParameterError(
                'LDAP_HOST setting was not found or passed as parameter during initialization')
        # if a username or password is not provided we error
        if not login:
            raise LDAPConfigurationParameterError('you must provide a login to authenticate')
        if not password:
            raise LDAPConfigurationParameterError('you must provide a password to authenticate')
        # Unlike connecting with NTLM we need the full DN for a user which we can't create from the login; as
        #   such we MUST bind using a bind_user_dn and bind_user_password.  We will then need to re-bind as
        #   the user once we get the users dn from searching.
        bind_user = self.bind_user
        bind_password = self.bind_password
        if not bind_user:
            raise LDAPConfigurationParameterError(
                'LDAP_BIND_DN setting was not found or passed as parameter during initialization')
        if not bind_password:
            raise LDAPConfigurationParameterError(
                'LDAP_BIND_PASSWORD setting was not found or passed as parameter during initialization')
        if not self.user_search_dn:
            raise LDAPConfigurationParameterError(
                'LDAP_USER_SEARCH_DN setting was not found or passed as parameter during initialization')
        if not self.user_search_query:
            raise LDAPConfigurationParameterError(
                'LDAP_USER_SEARCH_QUERY setting was not found or passed as parameter during initialization')
        # username = 'u:MYDOMAIN\\' + login
        # password = 'SettingsPasswordOrUserPassword'
        # user_search_dn = "OU=OFFICES,DC=example,DC=org"
        ldap_user = self.get_ldap_user_instance()

        server = self.get_ldap3_server()
        # Unlike AD; we always have to bind with a bind user to find the dn for the user with that login
        with Connection(server, bind_user, bind_password) as bind_conn:
            # we are bound as our bind user lets query the attributes of the login user
            bind_conn.search(self.user_search_dn, self.user_search_query.format(login),
                             attributes=['*'])
            # print(bind_conn)
            # print(bind_conn.entries)
            if bind_conn.entries:
                user_dn = bind_conn.entries[0]
            if user_dn:
                ldap_user.load(user_dn)
            # one additional step that is not needed for AD; re-bind as user now that we have dn to set is_authenticated
            #   since we originally bound as a bind user we haven't verified the password yet
            with Connection(server, ldap_user.dn, password) as conn:
                if conn.bound:
                    ldap_user.is_authenticated = True

        return ldap_user


# moving the operations for AD to a class
class ActiveDirectoryAuthenticator:
    """
    ActiveDirectoryAuthenticator will use NTLM (users login) to connect and search instead of normal LDAP DN
    """
    def __init__(self, host: str = None, bind_user: str = None, bind_password: str = None, ntlm_prefix: str = None,
                 ntlm_domain: str = None, user_search_dn: str = None, user_search_query: str = None):
        self.host = host or getattr(settings, 'LDAP_HOST', None)
        self.bind_user = bind_user or getattr(settings, 'AD_BIND_USER', None)
        self.bind_password = bind_password or getattr(settings, 'AD_BIND_PASSWORD', None)
        self.user_search_dn = user_search_dn or getattr(settings, 'LDAP_USER_SEARCH_DN', None)
        self.user_search_query = user_search_query or getattr(settings, 'LDAP_USER_SEARCH_QUERY', None)
        self.ntlm_domain = ntlm_domain or getattr(settings, 'AD_DOMAIN', None)
        self.ntlm_prefix = ntlm_prefix or getattr(settings, 'AD_USER_ID_PREFIX', None)

    def authenticate(self, username: str, password: str) -> LdapUser:
        return self.get_ldap_user(username, password)

    def fix_username(self, login: str) -> str:
        """
        Takes a login and turns it into an AD username that can be used for binding
        :param login: ex: mylogin
        :return: username to use for binding ex: u:MYDOMAIN\\mylogin
        """
        if login:
            if self.ntlm_domain and '\\' not in login:
                login = f'{self.ntlm_domain}\\{login}'
            if self.ntlm_prefix and not login.startswith(self.ntlm_prefix):
                login = f'{self.ntlm_prefix}{login}'
        return login

    def get_ldap3_server(self):
        """
        making a function so can be overridden if fine grained control is needed
        :return: ldap3 server instance
        """
        port = getattr(settings, 'LDAP_PORT', None)
        ssl = getattr(settings, 'LDAP_USE_SSL', True)
        if port:
            return Server(self.host, port=port, use_ssl=ssl, get_info=ALL)
        return Server(self.host, use_ssl=ssl, get_info=ALL)

    @staticmethod
    def get_ldap_user_instance():
        return LdapUser()

    def get_ldap_user(self, login: str, password: str = None) -> LdapUser:
        """
        Get an LdapUser by connecting to AD
        NOTE: user will not be is_authenticated if password isn't supplied and just looked up
        :param login: login from the login/password; ex: mylogin
        :param password: password from login/password
        :return:
        """
        # validate our settings to use for connecting
        # self.host = 'myldapserver.example.org'
        if not self.host:
            raise LDAPConfigurationParameterError(
                'LDAP_HOST setting was not found or passed as parameter during initialization')
        # if a username is not provided we error
        if not login:
            raise LDAPConfigurationParameterError('you must provide a login to authenticate against AD')
        # if a password is provided we will bind as the actual user instead of using the bind user; otherwise use
        #   the bind_user and bind_password and then lookup the user (should not be authenticated)
        if password:
            # bind_user=u:MYDOMAIN\\mylogin or MYDOMAIN\\mylogin or mylogin ; help by trying to fix syntax
            # bind_password = 'SettingsPasswordOrUserPassword'
            bind_user = self.fix_username(login)
            bind_password = password
        else:
            bind_user = self.fix_username(self.bind_user)
            bind_password = self.bind_password
            if not bind_user:
                raise LDAPConfigurationParameterError(
                    'AD_BIND_USER setting was not found or passed as parameter during initialization')
        if not self.user_search_dn:
            raise LDAPConfigurationParameterError(
                'LDAP_USER_SEARCH_DN setting was not found or passed as parameter during initialization')
        if not self.user_search_query:
            raise LDAPConfigurationParameterError(
                'LDAP_USER_SEARCH_QUERY setting was not found or passed as parameter during initialization')
        # username = 'u:MYDOMAIN\\' + login
        # user_search_dn = "OU=OFFICES,DC=example,DC=org"
        ldap_user = self.get_ldap_user_instance()

        server = self.get_ldap3_server()
        # try to bind with the user/pass given; test bad user bad password
        with Connection(server, user=bind_user, password=bind_password, authentication=NTLM, auto_bind=False) as conn:
            conn.bind()
            if conn.bound:
                if bind_user == self.fix_username(login):
                    ldap_user.is_authenticated = True
                # print(f'connection bound: {conn.bound}')
                # print(f'whoami: {conn.extend.standard.who_am_i()}')
                # query this persons attributes to fill our LdapUser object
                conn.search(self.user_search_dn, self.user_search_query.format(login),
                            attributes=['*'])
                # todo: instead of all attributes above build out the specific list here if it is faster
                # attributes=['cn', 'distinguishedName', 'email'])
                # print(conn)
                # print(conn.entries)
                if conn.entries:
                    user_dn = conn.entries[0]

                if user_dn:
                    ldap_user.load(user_dn)
                    # print(f'user_dn: {user_dn}')
                    # ldap_user.pprint()
            else:
                raise LDAPBindError('Provided username and password are incorrect!')

        return ldap_user


# CUSTOM BACKEND ADMIN OVERRIDE
class LdapBackend(BaseBackend):
    """
    Custom Backend to use the proper authenticator to try and login through external LDAP server and make sure the
        django user/groups objects are synced when logging into the admin
    """
    def authenticate(self, request, **kwargs):
        # username and password should be passed by login in kwargs
        # print(kwargs)
        # print(f"username: {kwargs.get('username')}")
        # print(f"password: {kwargs.get('password')}")
        username = kwargs.get('username')
        password = kwargs.get('password')
        # check the username/password and return the user
        # we are going to default to using AD type authentication since it only binds once and therefore is faster
        # use LDAP_AUTHENTICATION = DN to change (default = AD)
        if getattr(settings, 'LDAP_AUTHENTICATION', 'AD') != 'LDAP':
            authenticator = ActiveDirectoryAuthenticator()
        else:
            authenticator = LdapAuthenticator()

        try:
            ldap_user = authenticator.authenticate(username, password)
            # ldap_user.pprint()
        except LDAPException as lex:
            # we don't want to error on username/password problems as this will fall through to local password
            if 'username and password are incorrect' not in str(lex):
                print('Exception loading user record from LDAP')
                print(lex)
            return None
        user = None
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            if ldap_user.is_authenticated:
                # Create a new user. Let's set a hash password since it will fall back to django if AD is down.
                user = User(username=username)
                # we assume if they can authenticate with AD they are able to get to admin (staff is checked)
                #   since even contractors work on our behalf even if they aren't technically staff
                user.is_staff = True
                user.is_superuser = ldap_user.is_superuser()
                user.username = username
                user.set_password(str(uuid.uuid4()))
                user.email = ldap_user.email
                user.first_name = ldap_user.gn
                user.last_name = ldap_user.sn
                user.save()
        finally:
            # if we have a user and an ldap_user lets setup the groups
            if user and ldap_user.is_authenticated:
                authenticated_groups = getattr(settings, 'LDAP_AUTHENTICATED_GROUPS', [])
                try:
                    iter(authenticated_groups)
                except TypeError:
                    print(f'authenticated_groups was not iterable; resetting to empty list')
                    authenticated_groups = []
                # get a list of groups that match our ldap groups ignoring case
                app_groups = Group.objects.all()
                for group in app_groups:
                    igroup = group.name.strip().upper()
                    if igroup in ldap_user.groups or igroup in authenticated_groups:
                        # add these groups to the user if they don't exist
                        if group not in user.groups.all():
                            print(f'adding {group.name} to user...')
                            user.groups.add(group)
                            user.save()
                        else:
                            print(f'user already in {group.name}; skipping...')
        return user

    def get_user(self, user_id):
        # return the current user
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
