"""
Implement SSL Support in Kupfer using Python's 'ssl' module.
This plugin is named to be loaded first of all if it is activated.

This extension is not part of Kupfer itself because OpenSSL (Python's 'ssl')
is incompatible with the GNU GPLv3, even if both a open source. There is
nothing prohibiting a user to use this plugin.
"""
__kupfer_name__ = _("SSL Support")
__description__ = _("Enable OpenSSL support in Kupfer.")
__version__ = ""
__author__ = ""

import sys
from kupfer import pretty

# unblock openssl modules
for modname in ['ssl', '_ssl']:
    if sys.modules.get(modname, 1) is None:
        pretty.print_debug(__name__, "Unblocking module '%s'" % modname)
        del sys.modules[modname]

try:
    import ssl
except ImportError:
    ssl = None

import httplib

from kupfer import pretty

__all__ = ['VerifiedHTTPSConnection']


if ssl:
    # NOTE: Below we use inline imports so that the class is
    #       transferrable to another module without dependencies on
    #       module-globals!
    class VerifiedHTTPSConnection(httplib.HTTPConnection):
        """
        Raises RuntimeError if SSL is not supported
        """
        default_port = 443
        CA_CERT_LOCATIONS = (
            "/etc/ssl/certs/ca-certificates.crt", # Debian
            "/etc/pki/tls/certs/ca-bundle.crt",   # Red Hat
        )
        use_certificate_file = None

        def __init__(self, *args, **kwargs):
            import httplib
            if not self.is_ssl_supported():
                raise RuntimeError("SSL not supported")
            self.key_file = None
            self.cert_file = None
            httplib.HTTPConnection.__init__(self, *args, **kwargs)

        def connect(self):
            import ssl
            import socket
            sock = socket.create_connection((self.host, self.port),self.timeout)
            if self._tunnel_host:
                self.sock = sock
                self._tunnel()
            # wrap the socket using verification with the root
            self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file,
                 cert_reqs=ssl.CERT_REQUIRED, ca_certs=self.use_certificate_file)

        @classmethod
        def is_ssl_supported(cls):
            import os
            from kupfer import pretty

            if cls.use_certificate_file is not None:
                return True
            for caf in cls.CA_CERT_LOCATIONS:
                if os.path.exists(caf):
                    cls.use_certificate_file = caf
                    pretty.print_debug(__name__, "Using CA Certificates file", caf)
                    return True
            pretty.print_error(__name__, "SSL Error: No CA Certificates file found")
            return False

from kupfer.plugin import ssl_support
# "install" into kupfer.plugin.ssl_support
for x in __all__:
    setattr(ssl_support, x, globals().get(x,None))

