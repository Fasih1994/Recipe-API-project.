"""
Django command to wait for Database to be available
"""

from typing import Any, Union
import time
from psycopg2 import OperationalError as Psyocpg2Error
from django.db.utils import OperationalError
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """
    Django command to wait for Database
    """
    def handle(self, *args: Any, **options: Any) -> Union[str, None]:
        """Entry point for command"""
        # super().handle(*args, **options)
        self.stdout.write('Waiting for database...')
        db_up = False
        while db_up is False:
            try:
                self.check(databases=['default'])
                db_up = True
            except (Psyocpg2Error, OperationalError):
                self.stdout.write('Database unavilable, waiting for 1 second!')
                time.sleep(1)

        self.stdout.write(self.style.SUCCESS('Database Available!'))
