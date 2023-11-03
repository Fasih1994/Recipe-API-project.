"""
Test Custom Django mangement Commands
"""


from unittest.mock import patch, Mock

from psycopg2 import OperationalError as Psycopg2Error

from django.core.management import call_command
from django.db.utils import OperationalError
from django.test import SimpleTestCase


@patch('core.management.commands.wait_for_db.Command.check')
class CommandTest(SimpleTestCase):
    """Test Commands

    Args:
        SimpleTestCase (_type_): _description_
    """

    @patch('time.sleep')
    def test_wait_for_db_delay(self, patched_sleep: Mock, patched_check: Mock):
        """Test waiting for database if getting operational error"""
        patched_check.side_effect = [Psycopg2Error] * 2 + \
            [OperationalError] * 3 + [True]

        call_command('wait_for_db')

        self.assertEqual(patched_check.call_count, 6)

        patched_check.assert_called_with(databases=['default'])

    def test_wait_for_db_ready(self, patched_check: Mock):
        """Test waiting for database if ready"""
        patched_check.return_value = True

        call_command('wait_for_db')

        patched_check.assert_called_once_with(databases=['default'])
