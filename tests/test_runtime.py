import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import main
from job_tracker.adapters.base import AdapterError, RawJob
from job_tracker.config import AppConfig, CompanyConfig, Filters, Settings, load_config
from job_tracker.db import JobDatabase


class TestRuntime(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = str(Path(self.directory.name) / 'state.db')
        self.config = AppConfig(Settings(ntfy_topic='test', db_path=self.path), Filters(),
                                [CompanyConfig('Example', 'greenhouse')])
        self.job = RawJob('1', 'Hardware Intern', 'Austin, TX', 'https://example.com/jobs/1')

    def test_failed_delivery_retries_then_deduplicates_after_success(self):
        db = JobDatabase(self.path)
        self.addCleanup(db.close)
        adapter = Mock()
        adapter.fetch_jobs.return_value = [self.job]
        with patch('main.get_adapter', return_value=adapter), patch('main.NtfyNotifier') as notifier:
            notifier.return_value.send_notification.return_value = []
            self.assertEqual(main.check_companies(self.config, self.config.companies, db, False), 1)
            self.assertFalse(db.is_seen('Example', '1'))
            notifier.return_value.send_notification.side_effect = lambda matches, **kw: matches
            self.assertEqual(main.check_companies(self.config, self.config.companies, db, False), 0)
            self.assertTrue(db.is_seen('Example', '1'))
            notifier.return_value.send_notification.reset_mock()
            main.check_companies(self.config, self.config.companies, db, False)
            notifier.return_value.send_notification.assert_not_called()

    def test_failed_source_does_not_prevent_healthy_source_but_exits_nonzero(self):
        self.config.companies.append(CompanyConfig('Healthy', 'greenhouse'))
        broken, healthy = Mock(), Mock()
        broken.fetch_jobs.side_effect = AdapterError('HTTP 404')
        healthy.fetch_jobs.return_value = [self.job]
        db = JobDatabase(self.path)
        self.addCleanup(db.close)
        with patch('main.get_adapter', side_effect=[broken, healthy]), patch('main.NtfyNotifier') as notifier:
            notifier.return_value.send_notification.side_effect = lambda matches, **kw: matches
            self.assertEqual(main.check_companies(self.config, self.config.companies, db, False), 1)
            self.assertTrue(db.is_seen('Healthy', '1'))

    def test_dry_run_does_not_create_database(self):
        adapter = Mock()
        adapter.fetch_jobs.return_value = [self.job]
        with patch('main.load_config', return_value=self.config), patch('main.get_adapter', return_value=adapter), patch('requests.post') as post:
            self.assertEqual(main.main(['--dry-run']), 0)
            post.assert_not_called()
        self.assertFalse(Path(self.path).exists())

    def test_dry_run_does_not_change_existing_database(self):
        db = JobDatabase(self.path)
        db.mark_seen('Example', 'old', 'Old job', 'https://example.com/old')
        db.close()
        before = Path(self.path).read_bytes()
        adapter = Mock()
        adapter.fetch_jobs.return_value = [self.job]
        with patch('main.load_config', return_value=self.config), patch('main.get_adapter', return_value=adapter), patch('requests.post') as post:
            self.assertEqual(main.main(['--dry-run']), 0)
            post.assert_not_called()
        self.assertEqual(Path(self.path).read_bytes(), before)

    def test_live_run_without_topic_fails_before_scraping_or_creating_state(self):
        self.config.settings.ntfy_topic = ''
        with patch('main.load_config', return_value=self.config), patch('main.get_adapter') as adapter:
            self.assertEqual(main.main([]), 1)
            adapter.assert_not_called()
        self.assertFalse(Path(self.path).exists())

    def test_minimal_config_retains_filter_defaults_and_environment_overrides(self):
        path = Path(self.directory.name) / 'config.yaml'
        path.write_text('companies: []\n', encoding='utf-8')
        with patch.dict(os.environ, {'NTFY_TOPIC': 'private-test', 'JOB_DB_PATH': self.path}):
            config = load_config(str(path))
        self.assertEqual(config.filters, Filters())
        self.assertEqual(config.settings.ntfy_topic, 'private-test')
        self.assertEqual(config.settings.db_path, self.path)
