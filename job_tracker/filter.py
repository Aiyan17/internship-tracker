import re
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
    pattern = rf"\b{re.escape(keyword)}\b"
    return re.search(pattern, text, re.IGNORECASE) is not None


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
        desc_text = description or ""
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
        else:
            # Fallback: if location field is empty, check description for explicit US/Remote indicators
            if any(has_word(desc_text, loc_kw) for loc_kw in ["united states", "usa", "u.s.a.", "remote"]):
                loc_matched = True

        if not loc_matched:
            return None

        # 4. Visa & ITAR Warning Flagging (DO NOT DROP, only flag)
        found_flags = []
        combined_text = f"{title_text} {desc_text}"
        for visa_kw in self.filters.visa_flag_keywords:
            if has_word(combined_text, visa_kw) or visa_kw.lower() in combined_text.lower():
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
