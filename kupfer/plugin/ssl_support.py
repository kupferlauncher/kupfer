
import httplib
import os
import socket
import urllib

try:
	import ssl
except ImportError:
	ssl = None

CA_CERT_LOCATIONS = (
	"/etc/ssl/certs/ca-certificates.crt", # Debian
	"/etc/pki/tls/certs/ca-bundle.crt",   # Red Hat
)

from kupfer import pretty


if ssl:
	use_certificate_file = None
	class VerifiedHTTPSConnection(httplib.HTTPSConnection):
		"""
		Raises RuntimeError if SSL is not supported
		"""
		def __init__(self, *args, **kwargs):
			if not is_supported():
				raise RuntimeError("SSL not supported")
			httplib.HTTPSConnection.__init__(self, *args, **kwargs)

		def connect(self):
			sock = socket.create_connection((self.host, self.port),self.timeout)
			if self._tunnel_host:
				self.sock = sock
				self._tunnel()
			# wrap the socket using verification with the root
			self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file,
			     cert_reqs=ssl.CERT_REQUIRED, ca_certs=use_certificate_file)

	def is_supported():
		global use_certificate_file
		if use_certificate_file is not None:
			return True
		for caf in CA_CERT_LOCATIONS:
			if os.path.exists(caf):
				use_certificate_file = caf
				pretty.print_debug(__name__, "Using CA Certificates file", caf)
				return True
		pretty.print_error(__name__, "SSL Error: No CA Certificates file found")
		return False
else:
	def is_supported():
		return False
