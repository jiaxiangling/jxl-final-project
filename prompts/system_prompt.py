# -*- coding: utf-8 -*-
"""系统提示词构建器：按阶段拼装分节结构化提示词。"""

from typing import Any, Dict, Optional

from core.state import DifficultyState, LearnerProfile
from prompts.sections import (
    IDENTITY, USER_PROFILE, BOUNDARIES, TOOLS, MULTIMODAL,
    SAFETY, OUTPUT_FORMAT,
    learner_awareness_zh, learner_awareness_es,
)


def _learner_awareness(l1: str) -> str:
    if l1 == "es":
        return learner_awareness_es()
    return learner_awareness_zh()


def _current_context(profile: LearnerProfile, scenario: Optional[Dict[str, Any]],
                     difficulty: DifficultyState, turn_no: int) -> str:
    l1_label = "Spanish (Mexican)" if profile.l1 == "es" else "Chinese"
    scenario_info = "Free conversation (no specific scenario)" if not scenario else (
        f"Scenario: {scenario.get('name_en', 'N/A')} ({scenario.get('id', '')})\n"
        f"  Persona: {scenario.get('persona', 'N/A')}\n"
        f"  Target phrases: {', '.join(scenario.get('target_phrases', [])[:3])}"
    )
    return f"""=== CURRENT CONTEXT ===
- Learner L1: {l1_label}
- Current CEFR level: {difficulty.cefr}
- Speech speed: {difficulty.speed}x | Topic depth: {difficulty.topic_depth}
- Turn number: {turn_no}
- {scenario_info}
- Learner goals: {', '.join(profile.goals) if profile.goals else 'general improvement'}"""


def build_system_prompt(profile: LearnerProfile,
                        scenario: Optional[Dict[str, Any]] = None,
                        difficulty: Optional[DifficultyState] = None,
                        turn_no: int = 0,
                        phase: str = "in_lesson") -> str:
    """组装完整的系统提示词。"""
    if difficulty is None:
        difficulty = DifficultyState(cefr=profile.cefr)

    sections = [
        IDENTITY,
        USER_PROFILE,
        BOUNDARIES,
        _learner_awareness(profile.l1),
        _current_context(profile, scenario, difficulty, turn_no),
        TOOLS,
        MULTIMODAL,
        SAFETY,
        OUTPUT_FORMAT,
    ]
    return "\n\n".join(sections)


def build_assessment_prompt(profile: LearnerProfile) -> str:
    """课前测评阶段专用提示词。"""
    l1_label = "Spanish (Mexican)" if profile.l1 == "es" else "Chinese"
    return f"""=== IDENTITY & ROLE ===
You are an English proficiency assessor. Your job is to evaluate the learner's
English level across four dimensions: Listening, Speaking, Reading, Writing.
Score each dimension 0-100 and assign an overall CEFR level (A1-C2).

=== LEARNER INFO ===
- Native language: {l1_label}
- Age: {profile.age}
- Occupation: {profile.occupation}
- Self-assessed level: {profile.baseline_level}
- Goals: {', '.join(profile.goals) if profile.goals else 'N/A'}

=== BOUNDARIES ===
- Be objective and fair. Do not coach during assessment.
- Use adaptive difficulty: if the learner answers correctly, ask harder questions.

=== OUTPUT FORMAT ===
Return a JSON object:
{{"listening": 0-100, "speaking": 0-100, "reading": 0-100, "writing": 0-100,
  "overall_cefr": "A1-C2", "rationale": "brief explanation"}}"""


def build_feedback_prompt(mistakes: list, metrics: dict, scenario_id: str) -> str:
    """课后反馈阶段专用提示词。"""
    return f"""=== IDENTITY & ROLE ===
You are a learning analyst. Generate a practice session feedback report based on
the session data below.

=== SESSION DATA ===
- Scenario: {scenario_id}
- Total turns: {metrics.get('turns', 0)}
- Error rate: {metrics.get('error_rate', 0)}
- Tool calls: {metrics.get('tool_calls', 0)}
- Mistakes logged: {len(mistakes)}
- Mistake categories: {[m.get('category') for m in mistakes]}

=== OUTPUT FORMAT ===
Return a JSON object:
{{"summary": "overall summary", "strengths": ["..."], "weaknesses": ["..."],
  "key_phrases": ["..."], "new_words": ["..."], "cefr_delta": "+/- N",
  "encouragement": "motivational message"}}"""
