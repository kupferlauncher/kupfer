"""
Stub implementation of HTTPS connections.
"""

class VerifiedHTTPSConnection (object):
    "implementation stub"
    def __init__(self, host, *args, **kwargs):
        pass
    @classmethod
    def is_ssl_supported(cls):
        return False

def is_supported():
    return VerifiedHTTPSConnection and VerifiedHTTPSConnection.is_ssl_supported()
