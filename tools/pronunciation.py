# -*- coding: utf-8 -*-
"""L1 迁移感知发音评估工具：assess_pronunciation。"""

import json
import os
import re
from typing import Any, Dict, List

from config import DATA_DIR

_ERROR_PATTERNS: Dict[str, Any] = {}


def _load_patterns() -> Dict[str, Any]:
    global _ERROR_PATTERNS
    if not _ERROR_PATTERNS:
        path = os.path.join(DATA_DIR, "l1_error_patterns.json")
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                _ERROR_PATTERNS = json.load(f)
    return _ERROR_PATTERNS


def assess_pronunciation(transcript: str, learner_l1: str = "zh") -> Dict[str, Any]:
    """基于转写文本检测 L1 迁移发音/语法错误。

    注意：这是基于文本模式的启发式检测，非声学发音评分。
    Whisper 转写会将发音错误体现为错误词汇（如 think→sink）。
    """
    patterns = _load_patterns()
    l1_data = patterns.get(learner_l1, patterns.get("zh", {}))

    issues: List[Dict[str, Any]] = []
    text_lower = transcript.lower()

    # 检查发音模式
    for p in l1_data.get("pronunciation", []):
        pattern_str = p.get("pattern", "")
        if not pattern_str:
            continue
        # 用正则匹配
        try:
            tokens = pattern_str.split("|")
            for tok in tokens:
                tok = tok.strip()
                if tok and re.search(r"\b" + re.escape(tok) + r"\b", text_lower):
                    issues.append({
                        "type": "pronunciation",
                        "observed": tok,
                        "target": p.get("target", ""),
                        "explanation": p.get("note", ""),
                        "l1_cause": f"L1 transfer ({learner_l1})",
                        "example_incorrect": p.get("example_incorrect", ""),
                        "example_correct": p.get("example_correct", ""),
                    })
                    break
        except re.error:
            continue

    # 检查语法模式
    for g in l1_data.get("grammar", []):
        pattern_str = g.get("pattern", "")
        if not pattern_str:
            continue
        try:
            tokens = pattern_str.split("|")
            for tok in tokens:
                tok = tok.strip()
                if tok and re.search(r"\b" + re.escape(tok) + r"\b", text_lower):
                    issues.append({
                        "type": g.get("type", "grammar"),
                        "observed": tok,
                        "target": "correct grammar",
                        "explanation": g.get("note", ""),
                        "l1_cause": f"L1 transfer ({learner_l1})",
                        "example_incorrect": g.get("example_incorrect", ""),
                        "example_correct": g.get("example_correct", ""),
                    })
                    break
        except re.error:
            continue

    # 检查直译模式
    for t in l1_data.get("translation", []):
        pattern_str = t.get("pattern", "")
        if not pattern_str:
            continue
        try:
            tokens = pattern_str.split("|")
            for tok in tokens:
                tok = tok.strip()
                if tok and re.search(re.escape(tok), text_lower):
                    issues.append({
                        "type": "translation",
                        "observed": tok,
                        "target": "natural English",
                        "explanation": t.get("note", ""),
                        "l1_cause": f"L1 transfer ({learner_l1})",
                        "example_incorrect": t.get("example_incorrect", ""),
                        "example_correct": t.get("example_correct", ""),
                    })
                    break
        except re.error:
            continue

    # 计算分数
    issue_count = len(issues)
    word_count = max(len(transcript.split()), 1)
    # 简单评分：基础分 100，每个问题扣分（但与文本长度相关）
    penalty = min(issue_count * 12, 60)
    score = max(100 - penalty, 40)

    # 生成 tips
    tips: List[str] = []
    if any(i["type"] == "pronunciation" for i in issues):
        tips.append("Focus on tongue placement for sounds that don't exist in your L1.")
    if any(i["type"] == "grammar" for i in issues):
        tips.append("Practice sentence structure — especially articles, verb tenses, and subject-verb agreement.")
    if any(i["type"] == "translation" for i in issues):
        tips.append("Avoid direct translation from your native language — learn natural English collocations.")
    if not issues:
        tips.append("Great job! No major L1 transfer errors detected in this utterance.")

    return {
        "transcript": transcript,
        "learner_l1": learner_l1,
        "issues": issues[:6],  # 最多返回6个，避免信息过载
        "issue_count": issue_count,
        "score": score,
        "tips": tips,
        "method": "text-based L1 transfer pattern matching (not acoustic scoring)",
    }
