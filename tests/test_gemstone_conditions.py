import unittest
from app.utils.gemstone_conditions import matches_condition

class GemstoneConditionsTests(unittest.TestCase):
    def test_legacy_and_renamed_diamonds_match(self):
        for name in ('Natural Diamond', 'Natural diamonds ', 'NATURAL DIAMONDS', ' natural  diamonds '):
            self.assertTrue(matches_condition('primary_gemstone', name, 'Natural Diamond'))

    def test_non_diamonds_do_not_match(self):
        for name in ('Ruby', 'Lab Grown Diamond', '', None):
            self.assertFalse(matches_condition('primary_gemstone', name, 'Natural Diamond'))

    def test_other_fields_are_not_aliased(self):
        self.assertFalse(matches_condition('category', 'Natural Diamonds', 'Natural Diamond'))
