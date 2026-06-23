# -*- coding: utf-8 -*-
"""工具注册表：注册所有工具、导出 OpenAI function schema、执行分发。"""

import json
from typing import Any, Callable, Dict, List, Optional

from core.state import SessionState
from tools.dictionary import lookup_word, get_phonetics, expand_examples
from tools.patterns import suggest_sentence_patterns
from tools.pronunciation import assess_pronunciation
from tools.difficulty import adjust_difficulty
from tools.curriculum import get_scenario_curriculum, plan_learning_path
from tools.feedback import log_mistake, generate_session_feedback


# ── OpenAI function schemas ──────────────────────────
TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "lookup_word",
            "description": "Look up the definition, part of speech, and examples of an English word. Use when the learner uses or asks about an unfamiliar word.",
            "parameters": {
                "type": "object",
                "properties": {
                    "word": {"type": "string", "description": "The word to look up"},
                    "context": {"type": "string", "description": "The sentence context where the word appeared"},
                },
                "required": ["word"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_phonetics",
            "description": "Get the American English IPA pronunciation, syllables, and similar-sounding words for a given word.",
            "parameters": {
                "type": "object",
                "properties": {
                    "word": {"type": "string", "description": "The word to get phonetics for"},
                },
                "required": ["word"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_sentence_patterns",
            "description": "Suggest more natural American English sentence patterns when the learner's phrasing is unnatural, direct-translated, or too formal/informal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sentence": {"type": "string", "description": "The learner's original sentence"},
                    "intent": {"type": "string", "description": "The intended meaning or communicative intent"},
                },
                "required": ["sentence"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "expand_examples",
            "description": "Generate example sentences for a phrase to help the learner practice usage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "phrase": {"type": "string", "description": "The phrase to generate examples for"},
                    "count": {"type": "integer", "description": "Number of examples (default 3)", "default": 3},
                },
                "required": ["phrase"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "assess_pronunciation",
            "description": "Detect L1 transfer errors (pronunciation, grammar, translation) in the learner's utterance based on transcription patterns. Call every 2-3 turns.",
            "parameters": {
                "type": "object",
                "properties": {
                    "transcript": {"type": "string", "description": "The learner's transcribed utterance"},
                    "learner_l1": {"type": "string", "enum": ["zh", "es"], "description": "Learner's native language"},
                },
                "required": ["transcript", "learner_l1"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "adjust_difficulty",
            "description": "Adjust the conversation difficulty (CEFR level) based on the learner's recent performance. Lower when error rate is high, raise when fluent with few errors.",
            "parameters": {
                "type": "object",
                "properties": {
                    "current_level": {"type": "string", "enum": ["A1", "A2", "B1", "B2", "C1", "C2"], "description": "Current CEFR level"},
                    "recent_metrics": {
                        "type": "object",
                        "description": "Recent performance metrics",
                        "properties": {
                            "fluency": {"type": "number", "description": "Fluency score 0-5"},
                            "error_rate": {"type": "number", "description": "Error rate 0-1"},
                            "turns": {"type": "integer", "description": "Number of turns so far"},
                        },
                    },
                },
                "required": ["current_level"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "log_mistake",
            "description": "Log a grammar, pronunciation, vocabulary, or translation mistake for the learner's session summary. Always call when you identify an error.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "enum": ["pronunciation", "grammar", "vocabulary", "translation", "fluency"], "description": "Mistake category"},
                    "original": {"type": "string", "description": "The learner's incorrect utterance"},
                    "correction": {"type": "string", "description": "The corrected version"},
                    "l1_cause": {"type": "string", "description": "The L1 transfer cause if applicable"},
                },
                "required": ["category", "original", "correction"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_session_feedback",
            "description": "Generate a feedback summary at the end of a practice session. Call when the user wants to end the session.",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "The current session ID"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_scenario_curriculum",
            "description": "Retrieve the curriculum (objectives, vocabulary, model dialogue, tasks) for a specific scenario and CEFR level. Call at the start of a new scenario.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scenario_id": {"type": "string", "description": "The scenario ID (e.g., 'housing', 'interview')"},
                    "cefr_level": {"type": "string", "enum": ["A1", "A2", "B1", "B2", "C1", "C2"], "description": "Target CEFR level"},
                },
                "required": ["scenario_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "plan_learning_path",
            "description": "Design a personalized learning path based on the learner's profile and assessment results. Call during pre-class planning.",
            "parameters": {
                "type": "object",
                "properties": {
                    "profile": {"type": "object", "description": "Learner profile (l1, goals, pain_scenarios, cefr)"},
                    "assessment": {"type": "object", "description": "Assessment results (scores, overall_cefr)"},
                },
                "required": ["profile"],
            },
        },
    },
]


def get_schemas() -> List[Dict[str, Any]]:
    """返回 OpenAI tools 格式的 schema 列表。"""
    return TOOL_SCHEMAS


def execute_tool(name: str, args: Dict[str, Any],
                 session: Optional[SessionState] = None) -> Dict[str, Any]:
    """执行工具调用，返回 JSON 可序列化结果。

    Args:
        name: 工具名
        args: LLM 提供的参数
        session: 当前会话（用于补充上下文，如 metrics）
    """
    try:
        if name == "lookup_word":
            return lookup_word(args.get("word", ""), args.get("context", ""))

        if name == "get_phonetics":
            return get_phonetics(args.get("word", ""))

        if name == "suggest_sentence_patterns":
            return suggest_sentence_patterns(args.get("sentence", ""), args.get("intent", ""))

        if name == "expand_examples":
            return expand_examples(args.get("phrase", ""), args.get("count", 3))

        if name == "assess_pronunciation":
            l1 = args.get("learner_l1", "zh")
            if session and not l1:
                l1 = "zh"  # 可从 profile 获取
            return assess_pronunciation(args.get("transcript", ""), l1)

        if name == "adjust_difficulty":
            current = args.get("current_level", session.difficulty.cefr if session else "B1")
            metrics = args.get("recent_metrics")
            if not metrics and session:
                metrics = {
                    "fluency": session.metrics.get("fluency", 3.0),
                    "error_rate": session.metrics.get("error_rate", 0.2),
                    "turns": session.metrics.get("turns", 1),
                }
            elif not metrics:
                metrics = {"fluency": 3.0, "error_rate": 0.2, "turns": 1}
            return adjust_difficulty(current, metrics)

        if name == "log_mistake":
            result = log_mistake(
                args.get("category", "grammar"),
                args.get("original", ""),
                args.get("correction", ""),
                args.get("l1_cause", ""),
                session.scenario_id if session else "",
            )
            # 副作用：写入 session（由 orchestrator 处理，这里只返回结果+标记）
            result["_side_effect"] = "log_mistake"
            return result

        if name == "generate_session_feedback":
            if session:
                return generate_session_feedback(session.to_dict())
            return generate_session_feedback({"mistakes": [], "metrics": {}, "scenario_id": ""})

        if name == "get_scenario_curriculum":
            cefr = args.get("cefr_level", session.difficulty.cefr if session else "B1")
            return get_scenario_curriculum(args.get("scenario_id", ""), cefr)

        if name == "plan_learning_path":
            profile = args.get("profile", {})
            assessment = args.get("assessment", {})
            return plan_learning_path(profile, assessment)

        return {"error": f"Unknown tool: {name}"}

    except Exception as e:
        return {"error": f"Tool execution failed: {type(e).__name__}: {str(e)}"}


def get_tool_names() -> List[str]:
    """返回所有工具名。"""
    return [s["function"]["name"] for s in TOOL_SCHEMAS]
