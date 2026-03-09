# CUJ E2E Eval Framework (AI-EVAL-01)
#
# Defines Critical User Journey (CUJ) test scenarios as structured data.
# Each scenario describes an end-to-end flow through the Haven API with
# the expected API calls and outcomes.
#
# Phase 1: scenario definitions and structural validation only.
# Phase 2 (future): wire up an actual test client to execute the steps.

import sys
import unittest
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


# ---------------------------------------------------------------------------
# CUJ Scenario Data
# ---------------------------------------------------------------------------

CUJ_SCENARIOS: list[dict[str, Any]] = [
    {
        "name": "bind",
        "description": "User registration and partner pairing flow.",
        "steps": [
            {
                "action": "POST /api/auth/register",
                "payload": {"email": "alice@example.com", "password": "Test1234!"},
                "expected_status": 201,
                "required_fields": ["access_token", "user_id"],
            },
            {
                "action": "POST /api/auth/register",
                "payload": {"email": "bob@example.com", "password": "Test1234!"},
                "expected_status": 201,
                "required_fields": ["access_token", "user_id"],
            },
            {
                "action": "POST /api/pairing/invite",
                "payload": {},
                "expected_status": 200,
                "required_fields": ["invite_code"],
            },
            {
                "action": "POST /api/pairing/accept",
                "payload": {"invite_code": "<from_previous>"},
                "expected_status": 200,
                "required_fields": ["partner_pair_id"],
            },
        ],
        "expected_outcomes": {
            "final_status": "paired",
            "users_created": 2,
            "pair_established": True,
        },
    },
    {
        "name": "ritual",
        "description": "Daily card draw and respond ritual between partners.",
        "steps": [
            {
                "action": "POST /api/cards/draw",
                "payload": {"deck": "Daily Vibe"},
                "expected_status": 200,
                "required_fields": ["card_id", "question"],
            },
            {
                "action": "POST /api/cards/{card_id}/respond",
                "payload": {"response_text": "I feel grateful today."},
                "expected_status": 200,
                "required_fields": ["response_id"],
            },
        ],
        "expected_outcomes": {
            "card_drawn": True,
            "response_recorded": True,
        },
    },
    {
        "name": "journal",
        "description": "Create a journal entry and receive AI analysis.",
        "steps": [
            {
                "action": "POST /api/journals",
                "payload": {"content": "Today I felt grateful for my partner's support."},
                "expected_status": 201,
                "required_fields": ["journal_id"],
            },
            {
                "action": "GET /api/journals/{journal_id}/analysis",
                "payload": None,
                "expected_status": 200,
                "required_fields": [
                    "mood_label",
                    "emotional_needs",
                    "advice_for_user",
                    "action_for_user",
                    "advice_for_partner",
                    "action_for_partner",
                    "card_recommendation",
                    "safety_tier",
                ],
            },
        ],
        "expected_outcomes": {
            "journal_created": True,
            "analysis_returned": True,
            "safety_tier_range": [0, 3],
        },
    },
    {
        "name": "unlock",
        "description": "Both partners respond to a card, unlocking mutual reveal.",
        "steps": [
            {
                "action": "POST /api/cards/draw",
                "payload": {"deck": "Soul Dive"},
                "expected_status": 200,
                "required_fields": ["card_id", "question"],
            },
            {
                "action": "POST /api/cards/{card_id}/respond",
                "payload": {"response_text": "I appreciate your patience."},
                "expected_status": 200,
                "required_fields": ["response_id"],
                "actor": "user_a",
            },
            {
                "action": "POST /api/cards/{card_id}/respond",
                "payload": {"response_text": "I love our morning routine."},
                "expected_status": 200,
                "required_fields": ["response_id"],
                "actor": "user_b",
            },
            {
                "action": "GET /api/cards/{card_id}/reveal",
                "payload": None,
                "expected_status": 200,
                "required_fields": ["user_a_response", "user_b_response", "unlocked"],
            },
        ],
        "expected_outcomes": {
            "both_responded": True,
            "reveal_unlocked": True,
        },
    },
]


# ---------------------------------------------------------------------------
# Required fields per scenario / step for structural validation
# ---------------------------------------------------------------------------

REQUIRED_SCENARIO_FIELDS = {"name", "description", "steps", "expected_outcomes"}
REQUIRED_STEP_FIELDS = {"action", "expected_status", "required_fields"}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class CujScenarioStructureTests(unittest.TestCase):
    """Validate that all CUJ scenarios have the required structural fields."""

    def test_all_scenarios_have_required_fields(self) -> None:
        for scenario in CUJ_SCENARIOS:
            with self.subTest(scenario=scenario.get("name", "<unnamed>")):
                missing = REQUIRED_SCENARIO_FIELDS - set(scenario.keys())
                self.assertEqual(
                    missing,
                    set(),
                    f"Scenario '{scenario.get('name')}' is missing fields: {missing}",
                )

    def test_all_steps_have_required_fields(self) -> None:
        for scenario in CUJ_SCENARIOS:
            for idx, step in enumerate(scenario["steps"]):
                with self.subTest(scenario=scenario["name"], step_index=idx):
                    missing = REQUIRED_STEP_FIELDS - set(step.keys())
                    self.assertEqual(
                        missing,
                        set(),
                        f"Step {idx} in '{scenario['name']}' is missing: {missing}",
                    )

    def test_scenario_names_are_unique(self) -> None:
        names = [s["name"] for s in CUJ_SCENARIOS]
        self.assertEqual(len(names), len(set(names)), "Scenario names must be unique.")

    def test_at_least_four_scenarios(self) -> None:
        self.assertGreaterEqual(
            len(CUJ_SCENARIOS),
            4,
            "There should be at least 4 CUJ scenarios (bind, ritual, journal, unlock).",
        )

    def test_expected_status_codes_are_integers(self) -> None:
        for scenario in CUJ_SCENARIOS:
            for step in scenario["steps"]:
                with self.subTest(scenario=scenario["name"], action=step["action"]):
                    self.assertIsInstance(step["expected_status"], int)
                    self.assertIn(
                        step["expected_status"],
                        range(100, 600),
                        "Status code should be a valid HTTP status.",
                    )

    def test_required_fields_are_non_empty_lists(self) -> None:
        for scenario in CUJ_SCENARIOS:
            for step in scenario["steps"]:
                with self.subTest(scenario=scenario["name"], action=step["action"]):
                    self.assertIsInstance(step["required_fields"], list)
                    self.assertGreater(
                        len(step["required_fields"]),
                        0,
                        "required_fields must not be empty.",
                    )

    def test_expected_outcomes_is_dict(self) -> None:
        for scenario in CUJ_SCENARIOS:
            with self.subTest(scenario=scenario["name"]):
                self.assertIsInstance(scenario["expected_outcomes"], dict)
                self.assertGreater(len(scenario["expected_outcomes"]), 0)

    def test_known_scenarios_present(self) -> None:
        names = {s["name"] for s in CUJ_SCENARIOS}
        for required_name in ("bind", "ritual", "journal", "unlock"):
            self.assertIn(
                required_name,
                names,
                f"CUJ scenario '{required_name}' must be defined.",
            )

    def test_journal_analysis_requires_all_schema_fields(self) -> None:
        """The journal scenario's analysis step must check all JournalAnalysis fields."""
        journal_scenario = next(s for s in CUJ_SCENARIOS if s["name"] == "journal")
        analysis_step = journal_scenario["steps"][-1]

        expected_analysis_fields = {
            "mood_label",
            "emotional_needs",
            "advice_for_user",
            "action_for_user",
            "advice_for_partner",
            "action_for_partner",
            "card_recommendation",
            "safety_tier",
        }
        actual = set(analysis_step["required_fields"])
        missing = expected_analysis_fields - actual
        self.assertEqual(
            missing,
            set(),
            f"Journal analysis step is missing required_fields: {missing}",
        )


if __name__ == "__main__":
    unittest.main()
