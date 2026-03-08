import unittest
import sys

class TestImports(unittest.TestCase):
    def test_simple_term_menu_import(self):
        try:
            from simple_term_menu import TerminalMenu
        except ImportError:
            self.fail("simple_term_menu is not installed or cannot be imported")

if __name__ == "__main__":
    unittest.main()
