# pylint:disable=protected-access
# type:ignore

"""
Tests for validators.
"""
import unittest

from kupfer.support import validators as v


class TestValidateNetloc(unittest.TestCase):
    def test_ipv4(self):
        self.assertTrue(v.validate_netloc("127.0.0.1"))
        self.assertTrue(v.validate_netloc("0.0.0.0"))
        self.assertTrue(v.validate_netloc("255.255.255.255"))

        self.assertTrue(v.validate_netloc("@127.0.0.1"))
        self.assertTrue(v.validate_netloc("username@127.0.0.1"))
        self.assertTrue(v.validate_netloc("username:pass@127.0.0.1"))

        self.assertTrue(v.validate_netloc("127.0.0.1:123"))
        self.assertTrue(v.validate_netloc("@127.0.0.1:2314"))
        self.assertTrue(v.validate_netloc("username@127.0.0.1:21"))
        self.assertTrue(v.validate_netloc("username:pass@127.0.0.1:3"))

    def test_ipv4_neg(self):
        self.assertFalse(v.validate_netloc("127.0."))
        self.assertFalse(v.validate_netloc("127"))
        self.assertFalse(v.validate_netloc("276.0.0.0"))
        self.assertFalse(v.validate_netloc("255.255.255.255.244"))
        self.assertFalse(v.validate_netloc(":pass@127.0.0.1"))
        self.assertFalse(v.validate_netloc("@127.0.0.1:66666"))

    def test_ipv6(self):
        self.assertTrue(v.validate_netloc("[2001:db8:1::ab9:C:102]"))
        self.assertTrue(v.validate_netloc("[2001:db8:]"))
        self.assertTrue(v.validate_netloc("[::1]"))
        self.assertTrue(v.validate_netloc("[1:db8::1234:5678]"))
        self.assertTrue(v.validate_netloc("[::]"))

        self.assertTrue(v.validate_netloc("@[2001:db8:1::ab9:C:102]:12"))
        self.assertTrue(v.validate_netloc("user@[2001:db8:]:12"))
        self.assertTrue(v.validate_netloc("user:pass@[::1]:2131"))
        self.assertTrue(v.validate_netloc("[1:db8::1234:5678]:21312"))
        self.assertTrue(v.validate_netloc("[::]:1"))

    def test_ipv6_neg(self):
        # url need ipv6 address in [ ]
        self.assertFalse(v.validate_netloc("2001:db8:1::ab9:C:102"))

        self.assertFalse(v.validate_netloc("[2001]"))
        self.assertFalse(v.validate_netloc("[2:2:3:4:4:5:5:5:5:6]"))
        self.assertFalse(
            v.validate_netloc("[aaaa:bbbb:aaaa:bbbb:aaaa:bbbb:aaaa:bbbb:]")
        )
        self.assertFalse(
            v.validate_netloc("[aaaa:bbbb:aaaa:bbbb:aaaa:bbbb::aaaa:bbbb]")
        )
        self.assertFalse(
            v.validate_netloc("[aaaa:zbbb:aaaa:bbbb:aaaa:bbbb::azaa:bbbb]")
        )

    def test_hostname(self):
        self.assertTrue(v.validate_netloc("localhost"))
        self.assertTrue(v.validate_netloc("localhost:123"))
        self.assertTrue(v.validate_netloc("user@localhost"))
        self.assertTrue(v.validate_netloc("user:pass@localhost:123"))

        self.assertTrue(v.validate_netloc("www.abc.com"))
        self.assertTrue(v.validate_netloc("www.abc.com."))
        self.assertTrue(v.validate_netloc("www.abc-bc.com"))
        self.assertTrue(v.validate_netloc("www.ąśłóę.com"))
        self.assertTrue(v.validate_netloc("www.abc.com.pl"))
        self.assertTrue(v.validate_netloc("www.abc.com.pl:1234"))
        self.assertTrue(v.validate_netloc("user@www.abc.com.pl:1234"))
        self.assertTrue(v.validate_netloc("user:pass@www.abc.com.pl:1234"))

    def test_hostname_neg(self):
        self.assertTrue(v.validate_netloc("www.ab-c.com"))
        self.assertTrue(v.validate_netloc("www.abc--abc.com"))
        self.assertFalse(v.validate_netloc("anc*test.31231.com"))
        self.assertFalse(v.validate_netloc(".31231.com"))
        self.assertFalse(
            v.validate_netloc(
                ".123456789012345678901234567890123456789012345678901234567890.com"
            )
        )
        self.assertFalse(v.validate_netloc(".31231-.com"))
        self.assertFalse(v.validate_netloc("test@"))


class TestIsUrl(unittest.TestCase):
    def test_is_http_domain(self):
        self.assertTrue(v._is_http_domain("www.com"))
        self.assertTrue(v._is_http_domain("www.abc.com"))
        self.assertTrue(v._is_http_domain("www.abc.io"))
        self.assertTrue(v._is_http_domain("test.pl"))
        self.assertTrue(v._is_http_domain("test.com"))
        self.assertTrue(v._is_http_domain("localhost"))
        self.assertTrue(v._is_http_domain("ftp.localhost"))
        self.assertTrue(v._is_http_domain("abc.local"))
        self.assertTrue(v._is_http_domain("abc.local"))
        self.assertTrue(v._is_http_domain("abc.home.arpa"))

        self.assertFalse(v._is_http_domain("abcd"))
        self.assertFalse(v._is_http_domain("abc.xxxxxxxx"))
        self.assertFalse(v._is_http_domain("abc..local"))
        self.assertFalse(v._is_http_domain("abc.local."))
        self.assertFalse(v._is_http_domain(".abc.local"))

    def test_valid_http(self):
        self.assertEqual("https://www.abc.com", v.is_url("www.abc.com"))
        self.assertEqual("http://www.abc.com", v.is_url("http://www.abc.com"))
        self.assertEqual("http://abc.com", v.is_url("http://abc.com"))
        self.assertEqual(
            "https://abc.com/abc?test", v.is_url("abc.com/abc?test")
        )

        self.assertEqual("http://localhost", v.is_url("localhost"))
        self.assertEqual(
            "https://localhost/test", v.is_url("https://localhost/test")
        )

        self.assertEqual(
            "https://john.doe@www.example.com:123/forum/questions/"
            "?tag=networking&order=newest#top",
            v.is_url(
                "https://john.doe@www.example.com:123/forum/questions/"
                "?tag=networking&order=newest#top"
            ),
        )

    def test_valid_mail(self):
        self.assertEqual(
            "mailto:user@example.com",
            v.is_url("mailto:user@example.com"),
        )
        # "mail:" is invalid schema for email, but still valid url...
        # special case: fix to mailto
        self.assertEqual(
            "mailto:user@example.com",
            v.is_url("mail:user@example.com"),
        )

    def test_valid_other(self):
        self.assertEqual(
            "ftp://abc:123@localhost/test",
            v.is_url("ftp://abc:123@localhost/test"),
        )
        self.assertEqual(
            "ftp://abc:123@ftp.localhost/test",
            v.is_url("abc:123@ftp.localhost/test"),
        )

        self.assertEqual(
            "sftp://sftp.localhost/",
            v.is_url("sftp://sftp.localhost/"),
        )
        self.assertEqual(
            "sftp://test@localhost",
            v.is_url("sftp://test@localhost"),
        )
        self.assertEqual(
            "sftp://test@sftp.localhost/",
            v.is_url("sftp://test@sftp.localhost/"),
        )

        self.assertEqual(
            "ldap://[2001:db8::7]/c=GB?objectClass?one",
            v.is_url(
                "ldap://[2001:db8::7]/c=GB?objectClass?one",
            ),
        )
        self.assertEqual(
            "news:comp.infosystems.www.servers.unix",
            v.is_url("news:comp.infosystems.www.servers.unix"),
        )
        self.assertEqual(
            "telnet://192.0.2.16:80/",
            v.is_url(
                "telnet://192.0.2.16:80/",
            ),
        )

    def test_valid_http_neg(self):
        self.assertIsNone(v.is_url("www.abc"))
        self.assertIsNone(v.is_url("abcdds"))
        self.assertIsNone(v.is_url("http daldkal alkl"))
        self.assertIsNone(v.is_url("com."))

    def test_short_netloc(self):
        self.assertEqual("sftp://localhost", v.is_url("sftp://localhost"))
        self.assertEqual("sftp://test", v.is_url("sftp://test"))

    def test_invalid(self):
        self.assertIsNone(v.is_url("http://kla alsdalk"))
        self.assertIsNone(v.is_url("http://www.^abc"))
        self.assertIsNone(v.is_url("http://www.abc|dsl"))


class TestIsEmail(unittest.TestCase):
    def test_is_valid_email(self):
        self.assertTrue(v.is_valid_email("test@ldldl.com"))
        self.assertTrue(v.is_valid_email("test1w123@ldldl.com.pl"))

        self.assertFalse(v.is_valid_email("test@"))
        self.assertFalse(v.is_valid_email("@ldldl.com.pl"))
        self.assertFalse(v.is_valid_email("ldldl.com.pl"))
