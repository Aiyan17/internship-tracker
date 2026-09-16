import unittest
from job_tracker.config import Filters
from job_tracker.filter import JobFilter, has_word


class TestJobFilter(unittest.TestCase):
    def setUp(self):
        self.filters = Filters(
            role_keywords=["intern", "internship", "co-op", "coop"],
            topic_keywords=["power", "analog", "hardware", "pcb", "fpga", "electrical", "embedded", "battery", "validation", "test", "semiconductor", "silicon", "asic", "vlsi"],
            location_include=["united states", "us", "usa", "remote"],
            visa_flag_keywords=[
                "u.s. citizen", "us citizen", "u.s. person", "us person",
                "permanent resident", "green card", "without sponsorship",
                "no sponsorship", "sponsorship", "authorized to work",
                "security clearance", "itar", "export control", "citizenship"
            ]
        )
        self.filter_engine = JobFilter(self.filters)

    def test_word_boundary_helper(self):
        self.assertTrue(has_word("Austin, TX, US", "us"))
        self.assertFalse(has_word("Austin, TX", "us"))
        self.assertFalse(has_word("Internal Audit", "intern"))
        self.assertTrue(has_word("Software Engineering Intern", "intern"))
        self.assertFalse(has_word("Empower with PowerPoint", "power"))
        self.assertTrue(has_word("Low Power Analog IC", "power"))

    def test_valid_match_without_warning(self):
        match = self.filter_engine.evaluate_job(
            company="Micron",
            job_id="R100",
            title="Analog Design Intern - Summer 2027",
            location="Boise, ID, USA",
            url="https://micron.com/job/R100",
            description="Work on power management integrated circuits and analog validation."
        )
        self.assertIsNotNone(match)
        self.assertEqual(match.title, "Analog Design Intern - Summer 2027")
        self.assertFalse(match.visa_warning)

    def test_valid_match_with_expanded_visa_flags(self):
        match = self.filter_engine.evaluate_job(
            company="AMD",
            job_id="R200",
            title="Embedded Software Engineering Co-Op",
            location="Austin, TX, US",
            url="https://amd.com/job/R200",
            description="Must be authorized to work without sponsorship. ITAR compliance required."
        )
        self.assertIsNotNone(match)
        self.assertTrue(match.visa_warning)
        self.assertTrue(any("Sponsorship" in flag or "Itar" in flag for flag in match.visa_flags))

    def test_reject_internal_audit(self):
        match = self.filter_engine.evaluate_job(
            company="KLA",
            job_id="R300",
            title="Internal Audit Lead",
            location="Milpitas, CA, US",
            url="https://kla.com/job/R300",
            description="Hardware and accounting audit."
        )
        self.assertIsNone(match)

    def test_reject_austin_without_us(self):
        match = self.filter_engine.evaluate_job(
            company="onsemi",
            job_id="R400",
            title="Power Systems Intern",
            location="Austin, Australia",
            url="https://onsemi.com/job/R400",
            description="Location in Australia facility."
        )
        self.assertIsNone(match)


if __name__ == "__main__":
    unittest.main()
