#! /usr/bin/env python3
# pylint:disable
# type:ignore

"""

"""
import unittest

from . import validators as v


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
            v.validate_netloc("aaaa:bbbb:aaaa:bbbb:aaaa:bbbb:aaaa:bbbb:")
        )
        self.assertFalse(
            v.validate_netloc("aaaa:bbbb:aaaa:bbbb:aaaa:bbbb::aaaa:bbbb")
        )
        self.assertFalse(
            v.validate_netloc("aaaa:zbbb:aaaa:bbbb:aaaa:bbbb::azaa:bbbb")
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
