"""Siemens' public Avature search pages (not the retired Eightfold API)."""
from urllib.parse import urlencode, urljoin, urlparse

from bs4 import BeautifulSoup

from job_tracker.adapters.base import AdapterError, BaseAdapter, RawJob
from job_tracker.filter import has_word


class AvatureAdapter(BaseAdapter):
    def fetch_jobs(self):
        search_url = self.kwargs.get("search_url")
        if not search_url:
            raise AdapterError("Avature requires search_url")
        results = {}
        for term in self.kwargs.get("search_terms", ["intern", "co-op"]):
            url = search_url + "?" + urlencode({"search": term})
            visited = set()
            for _ in range(int(self.kwargs.get("max_pages", 500))):
                if url in visited:
                    raise AdapterError("Avature pagination repeated a page")
                visited.add(url)
                response = self.fetch_url(url)
                soup = BeautifulSoup(response.text, "html.parser")
                articles = soup.select("article.article--result")
                if not articles and not soup.select_one("#tpt_jobSortableForm"):
                    raise AdapterError("Unrecognized Avature search page")
                for article in articles:
                    anchor = article.select_one("h3 a[href]")
                    locations = article.select(".list-item-location")
                    if anchor is None or not locations:
                        raise AdapterError("Avature result is missing title or location")
                    job_url = urljoin(url, anchor["href"])
                    job_id = urlparse(job_url).path.rstrip("/").split("/")[-1]
                    if job_id in results:
                        continue
                    title = anchor.get_text(" ", strip=True)
                    description = ""
                    if any(has_word(title, word) for word in ("intern", "internship", "co-op", "coop")):
                        detail = BeautifulSoup(self.fetch_url(job_url).text, "html.parser")
                        sections = detail.select("article.article--details")
                        if not sections:
                            raise AdapterError(f"Unrecognized Avature detail page for {job_id}")
                        description = " ".join(section.get_text(" ", strip=True) for section in sections)
                    results[job_id] = RawJob(
                        job_id, title, "; ".join(loc.get_text(" ", strip=True) for loc in locations),
                        job_url, description,
                    )
                next_link = soup.find("a", string=lambda text: text and text.strip().startswith("Next"))
                if next_link is None:
                    break
                url = urljoin(url, next_link["href"])
                if urlparse(url).netloc != urlparse(search_url).netloc:
                    raise AdapterError("Avature pagination left the configured career site")
            else:
                raise AdapterError("Avature exceeded max_pages; result would be incomplete")
        return list(results.values())
