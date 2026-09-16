import time
import logging
import urllib.robotparser
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import requests

logger = logging.getLogger(__name__)


class RawJob:
    def __init__(
        self,
        job_id: str,
        title: str,
        location: str,
        url: str,
        description: str = ""
    ):
        self.job_id = job_id
        self.title = title
        self.location = location
        self.url = url
        self.description = description


class BaseAdapter(ABC):
    def __init__(
        self,
        company_name: str,
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) InternshipWatcher/1.0",
        delay_seconds: float = 1.5,
        **kwargs
    ):
        self.company_name = company_name
        self.user_agent = user_agent
        self.delay_seconds = delay_seconds
        self.kwargs = kwargs
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})
        self._robots_cache: Dict[str, urllib.robotparser.RobotFileParser] = {}

    def is_allowed_by_robots(self, url: str) -> bool:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = f"{parsed.scheme}://{parsed.netloc}"
            robots_url = f"{domain}/robots.txt"

            if domain not in self._robots_cache:
                rp = urllib.robotparser.RobotFileParser()
                rp.set_url(robots_url)
                try:
                    resp = self.session.get(robots_url, timeout=5)
                    if resp.status_code == 200:
                        rp.parse(resp.text.splitlines())
                    else:
                        rp.allow_all = True
                except Exception:
                    rp.allow_all = True
                self._robots_cache[domain] = rp

            rp = self._robots_cache[domain]
            if hasattr(rp, 'allow_all') and rp.allow_all:
                return True
            return rp.can_fetch(self.user_agent, url)
        except Exception as e:
            logger.debug(f"[{self.company_name}] Robots.txt check exception: {e}")
            return True  # Fallback to allowed on check failure

    def fetch_url(self, url: str, method: str = "GET", **kwargs) -> Optional[requests.Response]:
        if not self.is_allowed_by_robots(url):
            logger.warning(f"[{self.company_name}] Fetching {url} blocked by robots.txt rules.")
            return None

        if self.delay_seconds > 0:
            time.sleep(self.delay_seconds)

        try:
            if method.upper() == "POST":
                resp = self.session.post(url, timeout=15, **kwargs)
            else:
                resp = self.session.get(url, timeout=15, **kwargs)

            if resp.status_code == 403 or resp.status_code == 429:
                logger.warning(f"[{self.company_name}] Access blocked/rate-limited (HTTP {resp.status_code}) at {url}.")
                return None

            resp.raise_for_status()
            return resp
        except Exception as e:
            logger.error(f"[{self.company_name}] Failed to fetch {url}: {e}")
            return None

    @abstractmethod
    def fetch_jobs(self) -> List[RawJob]:
        """Fetch and return standardized raw jobs for this company."""
        pass
