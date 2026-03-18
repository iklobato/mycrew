"""Tests for my_script.py.
"""

import unittest
from my_script import greet

class TestMyScript(unittest.TestCase):

    def test_greet(self):
        self.assertEqual(greet("World"), "Hello, World!")
        self.assertEqual(greet("Python"), "Hello, Python!")
        self.assertEqual(greet(""), "Hello, !")
        self.assertEqual(greet("123"), "Hello, 123!")

if __name__ == '__main__':
    unittest.main()
