import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from job_tracker.filter import JobMatch
from job_tracker.notifier import NtfyNotifier


class TestNotifier(unittest.TestCase):
    def setUp(self):
        self.received = []
        self.statuses = []
        test = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers['Content-Length']))
                test.received.append((dict(self.headers), body))
                self.send_response(test.statuses.pop(0) if test.statuses else 200)
                self.end_headers()
                self.wfile.write(b'{}')

            def log_message(self, *args):
                pass

        self.server = HTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.notifier = NtfyNotifier('test', ntfy_url=f'http://127.0.0.1:{self.server.server_port}')

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def job(self, number, title='Hardware Intern'):
        return JobMatch('Example', str(number), title, 'Austin, TX', f'https://example.com/jobs/{number}')

    def test_real_http_request_accepts_unicode_body_and_ascii_headers(self):
        job = self.job(1, 'Hardware Intern – 電子')
        self.assertEqual(self.notifier.send_notification([job]), [job])
        headers, body = self.received[0]
        headers['Title'].encode('ascii')
        self.assertIn('電子', body.decode('utf-8'))

    def test_batches_are_limited_by_utf8_bytes(self):
        jobs = [self.job(i, 'Hardware Intern ' + '電' * 250) for i in range(12)]
        self.assertEqual(self.notifier.send_notification(jobs), jobs)
        self.assertGreater(len(self.received), 2)
        self.assertTrue(all(len(body) <= 4096 for _, body in self.received))

    def test_partial_failure_returns_only_successes_for_deduplication(self):
        jobs = [self.job(i) for i in range(3)]
        self.statuses = [200, 500, 200]
        self.assertEqual(self.notifier.send_notification(jobs, max_batch_size=1), [jobs[0], jobs[2]])

    def test_oversized_job_stays_unseen_and_does_not_block_other_jobs(self):
        jobs = [self.job(1, '電' * 2000), self.job(2)]
        self.assertEqual(self.notifier.send_notification(jobs), [jobs[1]])
        self.assertEqual(len(self.received), 1)

    def test_dry_run_never_posts(self):
        self.notifier.send_notification([self.job(1)], dry_run=True)
        self.assertEqual(self.received, [])
