import re
from html import unescape
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from typing import List, Optional
from job_tracker.config import Filters


@dataclass
class JobMatch:
    company: str
    job_id: str
    title: str
    location: str
    url: str
    description: str = ""
    resume_tag: str = ""
    visa_warning: bool = False
    visa_flags: List[str] = field(default_factory=list)


def has_word(text: str, keyword: str) -> bool:
    """Check if keyword matches as a whole word (case-insensitive)."""
    if not text or not keyword:
        return False
    # Use word boundaries \b for whole word matching
    pattern = rf"(?<!\w){re.escape(keyword)}(?!\w)"
    return re.search(pattern, text, re.IGNORECASE) is not None


US_STATES = (
    "Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|"
    "Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|"
    "Maine|Maryland|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|"
    "Nebraska|Nevada|New Hampshire|New Jersey|New Mexico|New York|North Carolina|"
    "North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|"
    "South Dakota|Tennessee|Texas|Utah|Vermont|Virginia|Washington|West Virginia|"
    "Wisconsin|Wyoming|District of Columbia"
)
US_CODES = (
    "AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|"
    "MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|DC"
)


def is_us_location(location: str) -> bool:
    if any(has_word(location, word) for word in ("united states", "usa", "us", "u.s.", "u.s.a.")):
        return True
    # Require a city + state pair, not arbitrary words such as "in" or the
    # country Georgia. Keep postal abbreviations uppercase to avoid prose.
    for part in re.split(r"[;|]", location):
        if re.search(rf"[^,]+,\s*(?:{US_CODES})(?:\s+\d{{5}}(?:-\d{{4}})?)?\s*$", part):
            return True
        if re.search(rf"[^,]+,\s*(?:{US_STATES})\s*$", part, re.IGNORECASE):
            return True
    return False


class JobFilter:
    def __init__(self, filters: Filters):
        self.filters = filters

    def evaluate_job(
        self,
        company: str,
        job_id: str,
        title: str,
        location: str,
        url: str,
        description: str = "",
        resume_tag: str = ""
    ) -> Optional[JobMatch]:
        title_text = title or ""
        desc_text = BeautifulSoup(unescape(description or ""), "html.parser").get_text(" ", strip=True)
        loc_text = location or ""

        # 1. Title MUST match at least one role keyword on a word boundary (e.g. intern, internship, co-op, coop)
        role_matched = any(has_word(title_text, r_kw) for r_kw in self.filters.role_keywords)
        if not role_matched:
            return None

        # 2. Topic Matching:
        # Require topic match in TITLE, OR at least 2 distinct topic matches in DESCRIPTION
        title_topic_matches = [t_kw for t_kw in self.filters.topic_keywords if has_word(title_text, t_kw)]
        desc_topic_matches = [t_kw for t_kw in self.filters.topic_keywords if has_word(desc_text, t_kw)]

        topic_matched = len(title_topic_matches) > 0 or len(set(desc_topic_matches)) >= 2
        if not topic_matched:
            return None

        # 3. Location Filter: Must be US or Remote (checking word boundaries)
        loc_matched = False
        if loc_text:
            loc_matched = any(has_word(loc_text, loc_kw) for loc_kw in self.filters.location_include)
            if any(k in self.filters.location_include for k in ("us", "usa", "united states")):
                loc_matched = loc_matched or is_us_location(loc_text)
        else:
            # Fallback: if location field is empty, check description for explicit US/Remote indicators
            if any(has_word(desc_text, loc_kw) for loc_kw in self.filters.location_include if loc_kw != "us"):
                loc_matched = True

        if not loc_matched:
            return None

        # 4. Visa & ITAR Warning Flagging (DO NOT DROP, only flag)
        found_flags = []
        combined_text = f"{title_text} {desc_text}"
        for visa_kw in self.filters.visa_flag_keywords:
            if has_word(combined_text, visa_kw):
                flag_title = visa_kw.title()
                if flag_title not in found_flags:
                    found_flags.append(flag_title)

        visa_warning = len(found_flags) > 0

        return JobMatch(
            company=company,
            job_id=job_id,
            title=title,
            location=location or "United States",
            url=url,
            description=description,
            resume_tag=resume_tag,
            visa_warning=visa_warning,
            visa_flags=found_flags
        )
