from gi.repository import Gtk

from kupfer import version, config, kupferstring
from kupfer.utils import show_url

class BaseDialogController(object):
    def __init__(self, ui, window_id):
        """Load ui from data file"""
        builder = Gtk.Builder()
        builder.set_translation_domain(version.PACKAGE_NAME)
        ui_file = config.get_data_file(ui)
        builder.add_from_file(ui_file)
        builder.connect_signals(self)
        self._builder = builder
        self.window = builder.get_object(window_id)

    def on_button_ok_clicked(self, widget):
        self.window.response(Gtk.ResponseType.ACCEPT)
        self.window.hide()

    def on_button_cancel_clicked(self, widget):
        self.window.response(Gtk.ResponseType.CANCEL)
        self.window.hide()

    def show(self):
        return self.window.run() == Gtk.ResponseType.ACCEPT

class CredentialsDialogController(BaseDialogController):
    def __init__(self, username, password, infotext=None):
        BaseDialogController.__init__(self, "credentials_dialog.ui",
                                                "credentials_dialog")
        self.entry_user = self._builder.get_object('entry_username')
        self.entry_pass = self._builder.get_object('entry_password')
        if infotext:
            hbox_information = self._builder.get_object('hbox_information')
            label_information = self._builder.get_object('label_information')
            hbox_information.show()
            label_information.set_text(infotext)

        self.entry_user.set_text(username or '')
        self.entry_pass.set_text(password or '')

    @property
    def username(self):
        return kupferstring.tounicode(self.entry_user.get_text())

    @property
    def password(self):
        return kupferstring.tounicode(self.entry_pass.get_text())


OUATH1_FIELDS = {'plugin_id', 'plugin_secret', 'verifier',
                     'url_auth', 'url_request', 'url_access', 'url_callback'}
OAUTH1_OUT_FIELDS = OUATH1_FIELDS - {'verifier'}

class OAuth1CredentialsDialogController(BaseDialogController):
    def __init__(self, oauth_cfg):
        BaseDialogController.__init__(self, "credentials_dialog_oauth1.ui",
                                                "oauth1_dialog")
        self._config = oauth_cfg
        self.entries = {}
        self.expect_new_token = False
        for k in OUATH1_FIELDS:
            self._set_entry(k)
        
    def _set_entry(self, key):
        entry = self._builder.get_object('entry_' + key)
        val = self._config.get(key, '') or ''
        entry.set_text(val)
        self.entries[key] = entry
        
    def _update_cfg(self, key):
        entry = self.entries[key]
        val = kupferstring.tounicode(entry.get_text())
        self._config[key] = val

    @property
    def config(self):
        for k in OAUTH1_OUT_FIELDS:
            self._update_cfg(k)
        return self._config
    
    def _oatuh1_session(self):
        global OAuth1Session
        if not 'OAuth1Session' in globals():
            from requests_oauthlib import OAuth1Session
        cfg = self.config.copy()
        entry_val = self.entries['verifier'].get_text()
        verifier = kupferstring.tounicode(entry_val)
        params = {
            "verifier": verifier,
            "client_secret": cfg.get('plugin_secret', None),
            "resource_owner_key": cfg.get('user_id', None),
            "resource_owner_secret": cfg.get('user_secret', None),
            "callback_uri": cfg.get('url_callback', None),
            "signature_method": cfg.get('signature_method', None),
            "signature_type": cfg.get('signature_type', None),
            "client_class": cfg.get('client_class', None),
            "force_include_body": cfg.get('force_include_body', None),
            "rsa_key": cfg.get('rsa_key', None)
        }
        p = {k: v for k, v in params.items() if v}
        return OAuth1Session(cfg['plugin_id'], **p)

    def on_button_new_token_clicked(self, widget):
        self._config['user_id'] = None
        self._config['user_secret'] = None
        self._config['verifier'] = None
        self._set_entry('verifier')
        oauth = self._oatuh1_session()
        tokens = oauth.fetch_request_token(self._config['url_request'])
        self._config['user_id'] = tokens.get('oauth_token')
        self._config['user_secret'] = tokens.get('oauth_token_secret')
        url = oauth.authorization_url(self._config['url_auth'])
        show_url(url)
        self.expect_new_token = True

    def on_button_ok_clicked(self, widget):
        if self.expect_new_token:
            oauth = self._oatuh1_session()
            access_url = self._config.get('url_access')
            tokens = oauth.fetch_access_token(access_url)
            self._config['user_id'] = tokens.get('oauth_token')
            self._config['user_secret'] = tokens.get('oauth_token_secret')
        BaseDialogController.on_button_ok_clicked(self, widget)


def ask_user_credentials(user=None, password=None, infotext=None):
    ''' Ask user for username and password.
    
    @user, @password - initial values
    @return:
    (user, password) when user press "change"
    None when user press "cancel" button '''
    dialog = CredentialsDialogController(user, password, infotext)
    if dialog.show():
        return dialog.username, dialog.password


def ask_user_oauth1_credentials(outh1_cfg):
    ''' Ask user for OAuth token autorization
    @outh1_cfg: informations to connect to oauth1:
    @return: same object with user_secret
    '''
    dialog = OAuth1CredentialsDialogController(outh1_cfg)
    if dialog.show():
        return dialog.config
