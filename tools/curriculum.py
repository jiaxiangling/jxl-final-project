# -*- coding: utf-8 -*-
"""课程与学习路径工具：get_scenario_curriculum / plan_learning_path。"""

import json
import os
from typing import Any, Dict, List

from config import DATA_DIR

_SCENARIOS: List[Dict[str, Any]] = []
_CURRICULUM: Dict[str, Any] = {}


def _load_scenarios() -> List[Dict[str, Any]]:
    global _SCENARIOS
    if not _SCENARIOS:
        path = os.path.join(DATA_DIR, "scenarios.json")
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                _SCENARIOS = json.load(f)
    return _SCENARIOS


def _load_curriculum() -> Dict[str, Any]:
    global _CURRICULUM
    if not _CURRICULUM:
        path = os.path.join(DATA_DIR, "curriculum.json")
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                _CURRICULUM = json.load(f)
    return _CURRICULUM


def get_scenario_curriculum(scenario_id: str, cefr_level: str = "B1") -> Dict[str, Any]:
    """获取场景课程内容。优先匹配指定 CEFR，降级取该场景任意级别。"""
    scenarios = _load_scenarios()
    scenario = next((s for s in scenarios if s["id"] == scenario_id), None)
    if not scenario:
        return {"error": f"Scenario '{scenario_id}' not found.", "available": [s["id"] for s in scenarios]}

    curriculum = _load_curriculum()
    scenario_curr = curriculum.get(scenario_id, {})

    # 优先匹配指定 CEFR，否则取第一个可用级别
    level_curr = scenario_curr.get(cefr_level)
    if not level_curr:
        # 降级：取任意可用级别
        for lvl, data in scenario_curr.items():
            level_curr = data
            cefr_level = lvl
            break
    if not level_curr:
        level_curr = {"objectives": [], "key_vocab": [], "model_dialogue": [], "tasks": [], "cultural_notes": []}

    return {
        "scenario": scenario,
        "level": cefr_level,
        "objectives": level_curr.get("objectives", []),
        "key_vocab": level_curr.get("key_vocab", []),
        "model_dialogue": level_curr.get("model_dialogue", []),
        "tasks": level_curr.get("tasks", []),
        "cultural_notes": scenario.get("cultural_notes", []) + level_curr.get("cultural_notes", []),
        "opening_lines": scenario.get("opening_lines", []),
        "target_phrases": scenario.get("target_phrases", []),
    }


def plan_learning_path(profile: Dict[str, Any], assessment: Dict[str, Any]) -> Dict[str, Any]:
    """基于画像与测评结果规划个性化学习路径。"""
    cefr = assessment.get("overall_cefr", profile.get("cefr", "B1"))
    l1 = profile.get("l1", "zh")
    goals = profile.get("goals", [])
    pain_scenarios = profile.get("pain_scenarios", [])

    # 场景优先级：痛点场景优先
    scenarios = _load_scenarios()
    priority_ids = [s["id"] for s in scenarios if s["id"] in pain_scenarios]
    other_ids = [s["id"] for s in scenarios if s["id"] not in pain_scenarios]
    ordered = priority_ids + other_ids

    # 分阶段规划
    phases: List[Dict[str, Any]] = []
    # 阶段1：基础场景（低难度痛点）
    phases.append({
        "name": "Phase 1: Foundation & Priority Scenarios",
        "focus": f"Build confidence in high-priority scenarios at {cefr} level",
        "scenarios": ordered[:3],
        "est_sessions": 6,
        "target_cefr": cefr,
    })
    # 阶段2：扩展场景
    next_cefr = _next_cefr(cefr)
    phases.append({
        "name": "Phase 2: Scenario Expansion",
        "focus": f"Expand to more scenarios, push toward {next_cefr}",
        "scenarios": ordered[3:6],
        "est_sessions": 8,
        "target_cefr": next_cefr,
    })
    # 阶段3：精进
    advanced_cefr = _next_cefr(next_cefr)
    phases.append({
        "name": "Phase 3: Fluency & Professional Contexts",
        "focus": f"Master complex scenarios, target {advanced_cefr}",
        "scenarios": ordered[6:] + ordered[:2],
        "est_sessions": 10,
        "target_cefr": advanced_cefr,
    })

    # 弱项建议（只取数值型分数，排除 overall_cefr 等字符串字段）
    raw_scores = assessment.get("scores", assessment)
    dim_scores = {k: v for k, v in raw_scores.items() if isinstance(v, (int, float))}
    weakest = min(dim_scores, key=dim_scores.get) if dim_scores else "speaking"
    l1_label = "Spanish" if l1 == "es" else "Chinese"

    return {
        "phases": phases,
        "rationale": (
            f"Starting at {cefr} (L1: {l1_label}). Priority on pain scenarios: "
            f"{', '.join(priority_ids) if priority_ids else 'none specified'}. "
            f"Weakest skill: {weakest} — extra focus recommended."
        ),
        "milestones": [
            {"after": "Phase 1", "goal": f"Handle basic {cefr} conversations in priority scenarios"},
            {"after": "Phase 2", "goal": f"Reach {next_cefr} across multiple scenarios"},
            {"after": "Phase 3", "goal": f"Fluent at {advanced_cefr} in professional contexts"},
        ],
        "focus_skill": weakest,
    }


def _next_cefr(cefr: str) -> str:
    levels = ["A1", "A2", "B1", "B2", "C1", "C2"]
    idx = levels.index(cefr) if cefr in levels else 2
    return levels[min(idx + 1, len(levels) - 1)]
