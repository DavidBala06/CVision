"""Tests for the deterministic weighted scorer."""
import pytest

from ai.scorer import (
    SKILL_MATCH_VALUES,
    WEIGHTS,
    _skill_match_type,
    rank_candidates,
    score_candidate,
    score_industry,
    score_location,
    score_seniority,
    score_skills,
    score_status,
)


def test_weights_sum_to_one():
    assert pytest.approx(sum(WEIGHTS.values()), abs=1e-9) == 1.0


class TestSkillMatchType:
    def test_exact_match(self):
        assert _skill_match_type("python", ["python", "go"]) == "exact"

    def test_synonym_match_is_exact(self):
        # "js" canonicalizes to "javascript"
        assert _skill_match_type("js", ["javascript"]) == "exact"

    def test_substring_is_similar(self):
        assert _skill_match_type("react", ["react-native"]) == "similar"

    def test_no_match(self):
        assert _skill_match_type("rust", ["python", "go"]) == "none"


class TestScoreSkills:
    def test_spreadsheet_example(self):
        """Replicate the example from the product spec:
        Python(1) + AWS(1) + FastAPI(0.8) = 2.8 / 3 = 93%"""
        required = ["python", "aws", "fastapi-like-framework"]
        candidate_techs = "python, aws, fastapi"
        score, breakdown = score_skills(required, candidate_techs)
        # python: exact (1.0), aws: exact (1.0), fastapi-like-framework: similar (0.8 — substring of fastapi)
        assert pytest.approx(score, abs=0.01) == 2.8 / 3
        assert [b["match"] for b in breakdown] == ["exact", "exact", "similar"]

    def test_all_exact(self):
        score, _ = score_skills(["python", "go"], "python, go, rust")
        assert score == 1.0

    def test_no_required_skills_perfect(self):
        score, _ = score_skills([], "anything")
        assert score == 1.0

    def test_no_matches(self):
        score, _ = score_skills(["rust", "haskell"], "python, go")
        assert score == 0.0


class TestScoreSeniority:
    def test_exact_match(self):
        assert score_seniority("senior", "senior") == 1.0

    def test_one_step_off(self):
        assert pytest.approx(score_seniority("senior", "mid_to_senior"), abs=0.01) == 0.75

    def test_two_steps_off(self):
        assert pytest.approx(score_seniority("senior", "mid"), abs=0.01) == 0.5

    def test_far_off_floor(self):
        assert score_seniority("lead", "intern") == 0.0  # 5 steps × 0.25 → clamped to 0

    def test_unknown_returns_neutral(self):
        assert score_seniority("", "senior") == 0.5
        assert score_seniority("senior", "wizard") == 0.5


class TestScoreLocation:
    def test_remote_overrides(self):
        assert score_location("Cluj", "Berlin", remote_ok=True) == 1.0

    def test_same_city(self):
        assert score_location("Cluj-Napoca", "Cluj-Napoca, Romania", remote_ok=False) == 1.0

    def test_same_country(self):
        assert score_location("Cluj, Romania", "Bucharest, Romania", remote_ok=False) == 0.6

    def test_different_country(self):
        assert score_location("Cluj, Romania", "Berlin, Germany", remote_ok=False) == 0.2

    def test_missing_returns_neutral(self):
        assert score_location("", "Cluj", remote_ok=False) == 0.5


class TestScoreIndustry:
    def test_strong_match(self):
        candidate = {"current_role": "ML Engineer at HuggingFace", "previous_jobs": "Senior AI Dev"}
        assert score_industry("ai", candidate) == 1.0

    def test_weak_match(self):
        candidate = {"project_summary": "Built a payment gateway"}
        # "payment" is in fintech keywords (1 hit)
        assert score_industry("fintech", candidate) == 0.7

    def test_no_match(self):
        candidate = {"current_role": "C++ developer", "technologies": "c++"}
        assert score_industry("healthcare", candidate) == 0.2

    def test_empty_required_neutral(self):
        assert score_industry("", {"current_role": "Anything"}) == 0.5


class TestScoreStatus:
    def test_active_full(self):
        assert score_status({"status": "active", "last_updated_at": "2026-05-01"}) == 1.0

    def test_pending_consent(self):
        assert score_status({"status": "pending_consent", "last_updated_at": "2026-05-01"}) == 0.6

    def test_stale_penalty(self):
        # 6+ months old → 0.8 multiplier
        assert pytest.approx(
            score_status({"status": "active", "last_updated_at": "2025-09-01"}), abs=0.01
        ) == 0.8


class TestScoreCandidate:
    def _baseline_requirements(self):
        return {
            "required_skills": ["python", "fastapi"],
            "min_seniority": "senior",
            "industry": "ai",
            "location": "Cluj-Napoca",
            "remote_ok": False,
        }

    def test_perfect_candidate_scores_high(self):
        candidate = {
            "name": "Ideal Dev",
            "seniority": "senior",
            "technologies": "python, fastapi, pytorch",
            "location": "Cluj-Napoca",
            "status": "active",
            "current_role": "ML Engineer",
            "previous_jobs": "Senior AI/ML Engineer",
            "last_updated_at": "2026-05-01",
        }
        result = score_candidate(candidate, self._baseline_requirements())
        assert result["matchScore"] >= 90
        assert result["matchRank"] == "Excellent"
        assert result["skillsScore"] == 100
        assert result["expScore"] == 100
        assert result["locationScore"] == 100
        assert result["statusScore"] == 100

    def test_partial_candidate_scores_proportionally(self):
        candidate = {
            "name": "Half Match",
            "seniority": "mid",
            "technologies": "python",
            "location": "Berlin",
            "status": "pending_consent",
            "current_role": "Dev",
            "last_updated_at": "2026-05-01",
        }
        result = score_candidate(candidate, self._baseline_requirements())
        # skills: 1/2 = 0.5 → 50
        assert result["skillsScore"] == 50
        # seniority: mid vs senior = 2 steps × 0.25 → 0.5 → 50
        assert result["expScore"] == 50
        # status: pending_consent = 0.6 → 60
        assert result["statusScore"] == 60
        # The weighted total should be lower than the perfect candidate.
        assert 0 < result["matchScore"] < 85

    def test_matchscore_uses_weights(self):
        candidate = {
            "name": "Skills Only",
            "seniority": "intern",
            "technologies": "python, fastapi",
            "location": "Berlin",
            "status": "pending_consent",
            "current_role": "Dev",
            "previous_jobs": "",
            "project_summary": "",
            "last_updated_at": "2026-05-01",
        }
        result = score_candidate(candidate, self._baseline_requirements())
        # Sanity-check the formula manually
        expected = (
            WEIGHTS["skills"] * 1.0       # all required skills present
            + WEIGHTS["seniority"] * 0.0  # intern vs senior = 4 steps × 0.25 = 1.0 → 0
            + WEIGHTS["industry"] * 0.2   # no industry keyword match
            + WEIGHTS["location"] * 0.2   # different country
            + WEIGHTS["status"] * 0.6     # pending_consent
        )
        assert pytest.approx(result["matchScore"] / 100, abs=0.01) == expected


class TestRankCandidates:
    def test_orders_by_total_score(self):
        candidates = [
            {"name": "Junior", "seniority": "junior", "technologies": "python", "location": "Berlin",
             "status": "pending_consent", "current_role": "Dev", "last_updated_at": "2026-05-01"},
            {"name": "Perfect", "seniority": "senior", "technologies": "python, fastapi", "location": "Cluj-Napoca",
             "status": "active", "current_role": "ML Engineer", "previous_jobs": "AI Engineer",
             "last_updated_at": "2026-05-01"},
        ]
        ranked = rank_candidates(candidates, {
            "required_skills": ["python", "fastapi"], "min_seniority": "senior",
            "industry": "ai", "location": "Cluj-Napoca", "remote_ok": False,
        })
        assert ranked[0]["name"] == "Perfect"
        assert ranked[0]["matchScore"] > ranked[1]["matchScore"]

    def test_returns_at_most_top_n(self):
        candidates = [{"name": f"C{i}", "seniority": "mid", "technologies": "python",
                       "location": "Cluj", "status": "active",
                       "current_role": "Dev", "last_updated_at": "2026-05-01"} for i in range(5)]
        ranked = rank_candidates(candidates, {"required_skills": ["python"], "min_seniority": "mid",
                                              "industry": "", "location": "Cluj", "remote_ok": False}, top_n=3)
        assert len(ranked) == 3
