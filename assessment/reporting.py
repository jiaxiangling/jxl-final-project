# -*- coding: utf-8 -*-
"""课后报告生成：单次会话反馈 + 周期性综合评估。"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.state import SessionState, load_user_sessions
from tools.feedback import generate_session_feedback


@dataclass
class SessionReport:
    """单次会话报告。"""
    summary: str = ""
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    key_phrases: List[str] = field(default_factory=list)
    new_words: List[str] = field(default_factory=list)
    mistakes_breakdown: Dict[str, int] = field(default_factory=dict)
    cefr_delta: str = "0"
    encouragement: str = ""
    scenario_id: str = ""
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PeriodicReport:
    """周期性综合评估报告。"""
    window: str = "7 days"
    total_sessions: int = 0
    total_turns: int = 0
    total_minutes: float = 0.0
    progress: str = ""
    short_boards: List[str] = field(default_factory=list)
    trend: str = ""
    recommendation: str = ""


def generate_session_report(session: SessionState) -> SessionReport:
    """生成单次会话反馈报告。"""
    data = session.to_dict()
    feedback = generate_session_feedback(data)

    return SessionReport(
        summary=feedback.get("summary", ""),
        strengths=feedback.get("strengths", []),
        weaknesses=feedback.get("weaknesses", []),
        key_phrases=feedback.get("key_phrases", []),
        new_words=feedback.get("new_words", []),
        mistakes_breakdown=feedback.get("mistakes_breakdown", {}),
        cefr_delta=feedback.get("cefr_delta", "0"),
        encouragement=feedback.get("encouragement", ""),
        scenario_id=session.scenario_id,
        metrics=session.metrics,
    )


def generate_periodic_report(user_id: str, days: int = 7) -> PeriodicReport:
    """生成周期性综合评估（基于历史会话）。"""
    sessions_meta = load_user_sessions(user_id)

    total_sessions = len(sessions_meta)
    total_turns = sum(s.get("turns", 0) for s in sessions_meta)
    total_minutes = total_turns * 3.0  # 估算：每轮约3分钟

    # 错误率趋势
    error_rates = [s.get("metrics", {}).get("error_rate", 0) for s in sessions_meta]

    if not sessions_meta:
        return PeriodicReport(
            window=f"{days} days",
            progress="No sessions found in this period. Start practicing!",
            recommendation="Begin with a scenario that matches your goals.",
        )

    # 进步分析
    if len(error_rates) >= 2:
        if error_rates[-1] < error_rates[0]:
            progress = f"Error rate improved from {error_rates[0]:.0%} to {error_rates[-1]:.0%}. Great progress!"
        else:
            progress = f"Error rate went from {error_rates[0]:.0%} to {error_rates[-1]:.0%}. Keep practicing to improve."
    else:
        progress = f"Completed {total_sessions} session(s). Consistency is key!"

    # 短板分析
    short_boards: List[str] = []
    if error_rates and error_rates[-1] > 0.4:
        short_boards.append("High error rate — review common mistakes and practice targeted scenarios.")
    if total_turns < 10:
        short_boards.append("Low practice volume — try longer conversation sessions.")

    # 趋势
    if error_rates:
        trend = "Improving" if len(error_rates) >= 2 and error_rates[-1] < error_rates[0] else "Steady"
    else:
        trend = "No data"

    recommendation = (
        f"Continue practicing {total_turns // max(total_sessions, 1)} turns per session. "
        f"Focus on your weakest scenarios and review logged mistakes."
    )

    return PeriodicReport(
        window=f"{days} days",
        total_sessions=total_sessions,
        total_turns=total_turns,
        total_minutes=round(total_minutes, 1),
        progress=progress,
        short_boards=short_boards,
        trend=trend,
        recommendation=recommendation,
    )
