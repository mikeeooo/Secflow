"""Exercise real file locking, which SQLite's shared-memory test DB cannot model."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
import tempfile
from threading import Event
from unittest import TestCase

from django.db import connection
from django.db.backends.sqlite3.base import DatabaseWrapper


class SQLiteConcurrencyTests(TestCase):
    def test_atomic_writers_wait_then_read_the_committed_value(self):
        config = deepcopy(connection.settings_dict)
        with tempfile.TemporaryDirectory() as folder:
            config['NAME'] = str(Path(folder) / 'concurrent.sqlite3')
            first = DatabaseWrapper(config, alias='locking_regression')
            attempted, read = Event(), Event()

            def second_writer():
                other = DatabaseWrapper(config, alias='locking_regression')
                try:
                    attempted.set()
                    other.set_autocommit(False, force_begin_transaction_with_broken_autocommit=True)
                    with other.cursor() as cursor:
                        cursor.execute('SELECT value FROM counter')
                        previous = cursor.fetchone()[0]
                        read.set()
                        cursor.execute('UPDATE counter SET value = %s', [previous + 1])
                    other.commit()
                    return previous
                finally:
                    other.close()

            try:
                with first.cursor() as cursor:
                    cursor.execute('CREATE TABLE counter (value INTEGER NOT NULL)')
                    cursor.execute('INSERT INTO counter VALUES (0)')
                first.set_autocommit(False, force_begin_transaction_with_broken_autocommit=True)
                with first.cursor() as cursor:
                    cursor.execute('SELECT value FROM counter')
                    self.assertEqual(cursor.fetchone()[0], 0)
                with ThreadPoolExecutor(max_workers=1) as pool:
                    pending = pool.submit(second_writer)
                    try:
                        self.assertTrue(attempted.wait(2))
                        self.assertFalse(read.wait(.1), 'A second writer read stale state before the first committed.')
                        with first.cursor() as cursor:
                            cursor.execute('UPDATE counter SET value = 1')
                        first.commit()
                    finally:
                        first.rollback()  # Also release the lock if an assertion fails.
                    self.assertEqual(pending.result(timeout=5), 1)
                with first.cursor() as cursor:
                    cursor.execute('SELECT value FROM counter')
                    self.assertEqual(cursor.fetchone()[0], 2)
            finally:
                first.close()
