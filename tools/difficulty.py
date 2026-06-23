# -*- coding: utf-8 -*-
"""难度自适应工具：adjust_difficulty。"""

from typing import Any, Dict

from config import CEFR_LEVELS


def adjust_difficulty(current_level: str, recent_metrics: Dict[str, Any]) -> Dict[str, Any]:
    """根据近期表现自主调整对话难度。

    Args:
        current_level: 当前 CEFR 级别
        recent_metrics: {fluency, error_rate, turns}

    Returns:
        新级别、原因、语速调整建议
    """
    error_rate = float(recent_metrics.get("error_rate", 0))
    fluency = float(recent_metrics.get("fluency", 0))
    turns = int(recent_metrics.get("turns", 0))

    idx = CEFR_LEVELS.index(current_level) if current_level in CEFR_LEVELS else 2  # 默认 B1

    new_idx = idx
    reason = "Maintaining current level."
    speed = _speed_for_level(current_level)
    topic_depth = "moderate"

    # 降级条件：错误率高
    if error_rate > 0.5:
        new_idx = max(0, idx - 1)
        reason = f"Error rate is high ({error_rate:.0%}) — lowering difficulty to build confidence."
        speed = _speed_for_level(CEFR_LEVELS[new_idx]) * 0.9
        topic_depth = "shallow"
    elif error_rate > 0.3:
        reason = f"Moderate error rate ({error_rate:.0%}) — keeping level but slowing down slightly."
        speed *= 0.95

    # 升级条件：连续多轮无错误且流利
    if error_rate < 0.1 and fluency >= 4.0 and turns >= 3:
        new_idx = min(len(CEFR_LEVELS) - 1, idx + 1)
        reason = f"Excellent performance (low errors, good fluency over {turns} turns) — raising difficulty."
        speed = _speed_for_level(CEFR_LEVELS[new_idx])
        topic_depth = "deep"

    new_level = CEFR_LEVELS[new_idx]
    changed = new_level != current_level

    return {
        "accepted": True,
        "prev_cefr": current_level,
        "new_cefr": new_level,
        "changed": changed,
        "reason": reason,
        "speed_adjustment": round(speed, 2),
        "topic_depth": topic_depth,
    }


def _speed_for_level(cefr: str) -> float:
    """CEFR 对应语速。"""
    speeds = {"A1": 0.85, "A2": 0.9, "B1": 1.0, "B2": 1.0, "C1": 1.05, "C2": 1.05}
    return speeds.get(cefr, 1.0)
