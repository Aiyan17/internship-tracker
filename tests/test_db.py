import os
import unittest
import tempfile
from job_tracker.db import JobDatabase


class TestJobDatabase(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.db = JobDatabase(self.temp_db.name)

    def tearDown(self):
        self.db.close()
        if os.path.exists(self.temp_db.name):
            os.remove(self.temp_db.name)

    def test_seen_and_mark_seen(self):
        company = "Micron"
        job_id = "JOB123"

        self.assertFalse(self.db.is_seen(company, job_id))
        marked = self.db.mark_seen(company, job_id, "Test Title", "http://example.com")
        self.assertTrue(marked)
        self.assertTrue(self.db.is_seen(company, job_id))

        # Duplicate insertion should return False and not fail
        marked_again = self.db.mark_seen(company, job_id, "Test Title", "http://example.com")
        self.assertFalse(marked_again)
        self.assertEqual(self.db.get_seen_count(), 1)


if __name__ == "__main__":
    unittest.main()
