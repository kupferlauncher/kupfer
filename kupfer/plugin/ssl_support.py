"""
Stub implementation of HTTPS connections.
"""


# pylint: disable=too-few-public-methods
class VerifiedHTTPSConnection:
    "implementation stub"

    def __init__(self, host, *args, **kwargs):
        pass

    @classmethod
    def is_ssl_supported(cls):
        return False


def is_supported():
    return (
        VerifiedHTTPSConnection  # type: ignore
        and VerifiedHTTPSConnection.is_ssl_supported()
    )
