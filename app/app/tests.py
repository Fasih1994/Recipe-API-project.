"""
Sample test
"""

from django.test import SimpleTestCase
from app import calc


class CalcTest(SimpleTestCase):
    """tests the calc module

    Args:
        SimpleTestCase (_type_): _description_
    """

    def test_add_numbers(self):
        """Test adding numbers together
        """
        res = calc.add_two(5, 6)
        self.assertEqual(res, 11)

    def test_sub_numbers(self):
        """test subtracting numbers
        """
        res = calc.sub_two(10, 15)
        self.assertEqual(res, 5)
