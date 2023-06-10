import unittest

from kupfer.support import itertools as kit


class TestTwoPartMapper(unittest.TestCase):
    def test1(self):
        def repfunc(string):
            print(string)
            self.assertEqual(len(string), 2)
            if string[0] == string[1]:
                return string.upper()

            return string

        # no changes
        self.assertEqual(
            kit.two_part_mapper("abbcdedeeffg123", repfunc), "abbcdedeeffg123"
        )
        self.assertEqual(
            kit.two_part_mapper("abbbcdedeeffg123", repfunc), "abBBcdedEEFFg123"
        )

    def test2(self):
        mapping = {
            "aa": "01",
            "bb": "23",
            "cc": "34",
        }

        def repfunc(string):
            return mapping.get(string)

        self.assertEqual(
            kit.two_part_mapper("abaabcdecccfag1aa", repfunc),
            "ab01bcde34cfag101",
        )
        self.assertEqual(
            kit.two_part_mapper("abbbcdedeeffg123", repfunc), "a23bcdedeeffg123"
        )
        self.assertEqual(
            kit.two_part_mapper("aaaaaaaaaaaaaaaa", repfunc), "0101010101010101"
        )
        self.assertEqual(
            kit.two_part_mapper("aabaabaabaab", repfunc), "01b01b01b01b"
        )
        self.assertEqual(
            kit.two_part_mapper("baabaabaabaab", repfunc), "b01b01b01b01b"
        )
        self.assertEqual(
            kit.two_part_mapper("baaabaaabaaabbaabb", repfunc),
            "b01ab01ab01a230123",
        )


class TestPeekfirst(unittest.TestCase):
    def test1(self):
        first, tail = kit.peekfirst([])
        self.assertIsNone(first)
        self.assertTrue(hasattr(tail, "__next__"))
        self.assertEqual([], list(tail))

        first, tail = kit.peekfirst([1, 2, 3, 4, 5])
        self.assertEqual(first, 1)
        self.assertTrue(hasattr(tail, "__next__"))
        self.assertEqual([1, 2, 3, 4, 5], list(tail))
