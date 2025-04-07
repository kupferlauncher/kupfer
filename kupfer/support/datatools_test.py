# Distributed under terms of the GPLv3 license.

"""
Test for datatools module.
"""

import unittest

from kupfer.support import datatools as d


class TestLruCache(unittest.TestCase):
    def test_insers(self):
        cache: d.LruCache[int, int] = d.LruCache(10)
        for i in range(5):
            cache[i] = i

        self.assertEqual(len(cache), 5)
        self.assertEqual(list(cache.keys()), [0, 1, 2, 3, 4])

        for i in range(10):
            cache[i] = i

        self.assertEqual(len(cache), 10)
        self.assertEqual(list(cache.keys()), [0, 1, 2, 3, 4, 5, 6, 7, 8, 9])

        for i in range(20):
            cache[i] = i

        self.assertEqual(len(cache), 10)
        self.assertEqual(
            list(cache.keys()), [10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
        )

        for i in range(10, 16):
            cache[i] = i

        self.assertEqual(len(cache), 10)
        self.assertEqual(
            list(cache.keys()), [16, 17, 18, 19, 10, 11, 12, 13, 14, 15]
        )

        for i in range(16, 20):
            self.assertEqual(cache[i], i)

        self.assertEqual(
            list(cache.keys()), [10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
        )

    def test_get_or_insert(self):
        cache: d.LruCache[int, int] = d.LruCache(10)

        # pylint: disable=too-few-public-methods
        class Creator:
            def __init__(self):
                self.cntr = 0

            def call(self):
                self.cntr += 1
                return self.cntr

        creator = Creator()

        val = cache.get_or_insert(0, creator.call)
        self.assertEqual(val, 1)

        val = cache.get_or_insert(0, creator.call)
        self.assertEqual(val, 1)

        val = cache.get_or_insert(1, creator.call)
        self.assertEqual(val, 2)

        val = cache.get_or_insert(2, creator.call)
        self.assertEqual(val, 3)

        val = cache.get_or_insert(1, creator.call)
        self.assertEqual(val, 2)

        val = cache.get_or_insert(0, creator.call)
        self.assertEqual(val, 1)

        self.assertEqual(creator.cntr, 3)
