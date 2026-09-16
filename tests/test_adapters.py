import unittest
from unittest.mock import Mock, patch

import requests

from job_tracker.adapters.base import AdapterError
from job_tracker.adapters.greenhouse import GreenhouseAdapter
from job_tracker.adapters.workday import WorkdayAdapter
from job_tracker.adapters.oracle import OracleAdapter
from job_tracker.adapters.avature import AvatureAdapter


class TestSourceErrors(unittest.TestCase):
    def setUp(self):
        self.adapter = GreenhouseAdapter(company_name='Example', board_token='example', delay_seconds=0)
        self.addCleanup(self.adapter.session.close)

    def test_http_failure_is_not_an_empty_job_list(self):
        response = requests.Response()
        response.status_code = 404
        response.url = 'https://example.com/jobs'
        with patch.object(self.adapter, 'is_allowed_by_robots', return_value=True), patch.object(self.adapter.session, 'get', return_value=response):
            with self.assertRaises(AdapterError):
                self.adapter.fetch_jobs()

    def test_html_instead_of_json_is_a_failure(self):
        response = requests.Response()
        response.status_code = 200
        response._content = b'<html>Moved careers site</html>'
        with patch.object(self.adapter, 'fetch_url', return_value=response):
            with self.assertRaises(AdapterError):
                self.adapter.fetch_jobs()

    def test_unexpected_json_shape_is_a_failure(self):
        with patch.object(self.adapter, 'fetch_json', return_value={'error': 'board missing'}):
            with self.assertRaises(AdapterError):
                self.adapter.fetch_jobs()

    def test_valid_empty_board_is_successful(self):
        with patch.object(self.adapter, 'fetch_json', return_value={'jobs': []}):
            self.assertEqual(self.adapter.fetch_jobs(), [])

    def test_robots_denial_is_reported_without_fetching_jobs(self):
        with patch.object(self.adapter, 'is_allowed_by_robots', return_value=False), patch.object(self.adapter.session, 'get') as get:
            with self.assertRaises(AdapterError):
                self.adapter.fetch_jobs()
            get.assert_not_called()


class TestWorkday(unittest.TestCase):
    def test_missing_page_is_not_a_successful_empty_search(self):
        adapter = WorkdayAdapter(company_name='Example', subdomain='example.wd1.myworkdayjobs.com')
        self.addCleanup(adapter.session.close)
        with patch.object(adapter, 'fetch_json', return_value={'total': 40, 'jobPostings': []}):
            with self.assertRaises(AdapterError):
                adapter.fetch_jobs()

    def test_paginates_past_sixty_and_uses_detail_country(self):
        adapter = WorkdayAdapter(company_name='Example', subdomain='example.wd1.myworkdayjobs.com', delay_seconds=0)
        self.addCleanup(adapter.session.close)
        offsets = []
        def fetch(url, method='GET', **kwargs):
            if method == 'POST':
                query = kwargs['json']
                if query['searchText'] == 'co-op':
                    return {'total': 0, 'jobPostings': []}
                offsets.append(query['offset'])
                return {'total': 61, 'jobPostings': [
                    {'title': 'Hardware Intern', 'locationsText': 'Boise',
                     'externalPath': f'/job/boise/Intern_{i}', 'bulletFields': [str(i)]}
                    for i in range(query['offset'], min(query['offset'] + 20, 61))]}
            return {'jobPostingInfo': {'location': 'Boise', 'country': {'descriptor': 'United States'},
                                       'jobDescription': 'Hardware and power design'}}
        with patch.object(adapter, 'fetch_json', side_effect=fetch):
            jobs = adapter.fetch_jobs()
        self.assertEqual(offsets, [0, 20, 40, 60])
        self.assertEqual(len(jobs), 61)
        self.assertEqual(jobs[0].location, 'Boise; United States')

    def test_page_limit_does_not_silently_report_complete_results(self):
        adapter = WorkdayAdapter(company_name='Example', subdomain='example.wd1.myworkdayjobs.com', max_pages=1)
        self.addCleanup(adapter.session.close)
        with patch.object(adapter, 'fetch_json', return_value={
            'total': 100, 'jobPostings': [{'title': 'Engineer', 'bulletFields': ['1']}]}):
            with self.assertRaises(AdapterError):
                adapter.fetch_jobs()


class TestOracle(unittest.TestCase):
    def test_pagination_details_and_job_links(self):
        adapter = OracleAdapter(company_name='TI', api_base='https://example.com/api',
                                site_url='https://careers.example.com', search_terms=['intern'])
        self.addCleanup(adapter.session.close)
        calls = []
        def fetch(url, **kwargs):
            calls.append((url, kwargs))
            if url.endswith('Details'):
                return {'items': [{'ExternalDescriptionStr': 'Hardware power intern',
                                   'ExternalQualificationsStr': 'Must be a U.S. person'}]}
            second = 'offset=50' in kwargs['params']['finder']
            return {'items': [{'TotalJobsCount': 51, 'requisitionList': [
                {'Id': '2' if second else '1', 'Title': 'Hardware Intern', 'PrimaryLocation': 'Dallas, TX'}]}]}
        with patch.object(adapter, 'fetch_json', side_effect=fetch):
            jobs = adapter.fetch_jobs()
        self.assertEqual(len(jobs), 2)
        self.assertEqual(jobs[0].url, 'https://careers.example.com/en/sites/CX/job/1')
        self.assertIn('U.S. person', jobs[0].description)
        self.assertEqual(len(calls), 4)


class TestAvature(unittest.TestCase):
    def test_follows_next_link_and_extracts_description(self):
        adapter = AvatureAdapter(company_name='Siemens', search_url='https://example.com/SearchJobs', search_terms=['intern'])
        self.addCleanup(adapter.session.close)
        def fetch(url):
            if '/JobDetail/' in url:
                return Mock(text='<article class="article--details">Electrical power design internship</article>')
            number = '2' if 'folderOffset' in url else '1'
            next_link = '<a href="/SearchJobs/intern?folderOffset=6">Next &gt;&gt;</a>' if number == '1' else ''
            return Mock(text=f'<article class="article--result"><h3><a href="/JobDetail/{number}">Hardware Intern</a></h3>'
                             f'<span class="list-item-location">Austin, Texas, United States</span></article>{next_link}')
        with patch.object(adapter, 'fetch_url', side_effect=fetch):
            jobs = adapter.fetch_jobs()
        self.assertEqual([j.job_id for j in jobs], ['1', '2'])
        self.assertEqual(jobs[0].description, 'Electrical power design internship')

    def test_unrecognized_page_fails(self):
        adapter = AvatureAdapter(company_name='Siemens', search_url='https://example.com/SearchJobs')
        self.addCleanup(adapter.session.close)
        with patch.object(adapter, 'fetch_url', return_value=Mock(text='<html>Error</html>')):
            with self.assertRaises(AdapterError):
                adapter.fetch_jobs()

    def test_exceeding_max_pages_returns_partial_results_instead_of_failing(self):
        # Siemens' public search has no server-side way to scope beyond a raw
        # keyword match (999+ results for "intern" alone), so any page cap
        # small enough to run in a bounded time will always be hit. Treat
        # that as a coverage warning, not a hard failure of the whole company.
        adapter = AvatureAdapter(
            company_name='Siemens', search_url='https://example.com/SearchJobs',
            search_terms=['intern'], max_pages=1,
        )
        self.addCleanup(adapter.session.close)

        def fetch(url):
            if '/JobDetail/' in url:
                return Mock(text='<article class="article--details">Electrical power design internship</article>')
            return Mock(text='<article class="article--result">'
                             '<h3><a href="/JobDetail/1">Hardware Intern</a></h3>'
                             '<span class="list-item-location">Austin, Texas, United States</span></article>'
                             '<a href="/SearchJobs/intern?folderOffset=6">Next &gt;&gt;</a>')
        with patch.object(adapter, 'fetch_url', side_effect=fetch):
            jobs = adapter.fetch_jobs()
        self.assertEqual([j.job_id for j in jobs], ['1'])
