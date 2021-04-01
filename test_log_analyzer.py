# -*- coding: utf-8 -*-
"""Unit tests for loag_analyzer.py"""

import unittest
import pycodestyle
import log_analyzer as la


class TestCode(unittest.TestCase):
    """TestCode"""

    def test_conformance(self):
        """Test that we conform to PEP-8."""
        style = pycodestyle.StyleGuide(quiet=True, config_file='tox.ini')
        result = style.check_files([la.__file__])
        self.assertEqual(result.total_errors, 0,
                         "Found code style errors (and warnings).")

    def test_app(self):
        """Test App"""
        d = {'App': {'TEST': 'pass'}}
        save_path = "tests/save_config.ini"
        la.App.save_config(save_path, d)
        r = la.App.load_config(save_path)
        self.assertTrue(len(d) == len(r) == len(list(k for k in d if k in r and d[k] == r[k])), "Saved dict is not the same as loaded.")


class TestMainCode(unittest.TestCase):
    """Test main"""

    def test_main(self):
        """Test main"""
        la.App.init("tests/log_test.ini")
        self.assertTrue(la.main(la.App.cfg) >= 0, "Main functionality is failed.")


if __name__ == '__main__':
    unittest.main()
