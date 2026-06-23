# -*- coding: utf-8 -*-
"""错误记录与会话反馈工具：log_mistake / generate_session_feedback。"""

from typing import Any, Dict, List


def log_mistake(category: str, original: str, correction: str,
                l1_cause: str = "", scenario: str = "") -> Dict[str, Any]:
    """记录一条错误（供课后汇总）。实际落库由 orchestrator 处理。"""
    valid_categories = ["pronunciation", "grammar", "vocabulary", "translation", "fluency"]
    if category not in valid_categories:
        category = "grammar"

    return {
        "logged": True,
        "category": category,
        "original": original,
        "correction": correction,
        "l1_cause": l1_cause,
        "scenario": scenario,
        "message": f"Logged {category} mistake: '{original}' → '{correction}'",
    }


def generate_session_feedback(session_data: Dict[str, Any]) -> Dict[str, Any]:
    """基于会话数据生成单次练习反馈。离线模式用规则模板。"""
    mistakes: List[Dict[str, Any]] = session_data.get("mistakes", [])
    metrics: Dict[str, Any] = session_data.get("metrics", {})
    scenario_id = session_data.get("scenario_id", "free_conversation")
    vocab: List[Dict[str, Any]] = session_data.get("vocab", [])
    turns = metrics.get("turns", 0)
    error_rate = metrics.get("error_rate", 0)
    tool_calls = metrics.get("tool_calls", 0)

    # 错误分类统计
    category_count: Dict[str, int] = {}
    for m in mistakes:
        cat = m.get("category", "grammar")
        category_count[cat] = category_count.get(cat, 0) + 1

    # 强项与弱项
    strengths: List[str] = []
    weaknesses: List[str] = []
    if error_rate < 0.2:
        strengths.append("Low error rate — good accuracy in this session.")
    elif error_rate > 0.4:
        weaknesses.append(f"Error rate was {error_rate:.0%} — focus on accuracy.")

    if turns >= 8:
        strengths.append(f"Sustained a {turns}-turn conversation — great persistence!")
    elif turns < 3:
        weaknesses.append("Short session — try to engage in longer conversations.")

    # 最常见错误类型
    if category_count:
        top_cat = max(category_count, key=category_count.get)
        cat_labels = {
            "pronunciation": "pronunciation (L1 transfer sounds)",
            "grammar": "grammar (articles, tenses, agreement)",
            "vocabulary": "vocabulary (word choice)",
            "translation": "translation (direct translation from L1)",
            "fluency": "fluency (pauses, hesitations)",
        }
        weaknesses.append(f"Most frequent issue: {cat_labels.get(top_cat, top_cat)} ({category_count[top_cat]} times).")

    if not strengths:
        strengths.append("You completed a practice session — keep going!")
    if not weaknesses:
        weaknesses.append("No major weaknesses detected — maintain consistent practice.")

    # 重点句型（从纠错中提取）
    key_phrases = list({m.get("correction", "") for m in mistakes if m.get("correction")})[:5]
    if not key_phrases:
        key_phrases = ["Practice common greetings and follow-up questions."]

    # 生词
    new_words = [v.get("word", "") for v in vocab if not v.get("mastered", False)][:8]

    # CEFR 变化
    difficulty_log = session_data.get("difficulty", {}).get("history", [])
    cefr_delta = "0"
    if difficulty_log:
        first = difficulty_log[0].get("from", "")
        last = difficulty_log[-1].get("to", "")
        from config import CEFR_NUMERIC
        if first in CEFR_NUMERIC and last in CEFR_NUMERIC:
            delta = CEFR_NUMERIC[last] - CEFR_NUMERIC[first]
            cefr_delta = f"{'+' if delta >= 0 else ''}{delta}"

    # 鼓励语
    encouragements = [
        "Every conversation makes you stronger. You're building real communication skills!",
        "Progress isn't always linear, but you showed up and practiced — that's what counts.",
        "Your willingness to practice is the key to fluency. Keep going!",
    ]
    encouragement = encouragements[turns % len(encouragements)]

    return {
        "summary": (
            f"In this {turns}-turn {'scenario: ' + scenario_id if scenario_id else 'free'} practice, "
            f"you made {len(mistakes)} mistake(s) with an error rate of {error_rate:.0%}. "
            f"The AI coach used {tool_calls} tool call(s) to assist you."
        ),
        "strengths": strengths,
        "weaknesses": weaknesses,
        "key_phrases": key_phrases,
        "new_words": new_words,
        "mistakes_breakdown": category_count,
        "cefr_delta": cefr_delta,
        "encouragement": encouragement,
    }
