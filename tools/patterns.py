# -*- coding: utf-8 -*-
"""地道句型替换工具：suggest_sentence_patterns。"""

from typing import Any, Dict

# 常见中式/西式直译 → 地道美式表达 模板库
_PATTERN_FIXES = [
    # 中文母语常见
    {"trigger": ["i want", "i want to"], "alternatives": [
        {"pattern": "would like", "sentence": "I'd like to...", "note": "More polite than 'I want'"},
        {"pattern": "I'm looking to", "sentence": "I'm looking to...", "note": "Natural for expressing intentions"},
    ]},
    {"trigger": ["open the light", "close the light"], "alternatives": [
        {"pattern": "turn on/off", "sentence": "turn on/off the light", "note": "Use 'turn on/off' for lights/devices, not 'open/close'"},
    ]},
    {"trigger": ["play with phone", "play phone"], "alternatives": [
        {"pattern": "look at", "sentence": "look at your phone", "note": "'Play' is for games/toys, not phones"},
    ]},
    {"trigger": ["i no like", "i no want"], "alternatives": [
        {"pattern": "don't", "sentence": "I don't like / I don't want", "note": "Use auxiliary 'don't' for negation"},
    ]},
    {"trigger": ["how to say", "how say"], "alternatives": [
        {"pattern": "How do I say", "sentence": "How do I say...?", "note": "Proper question structure with 'do'"},
    ]},
    {"trigger": ["can you help me to"], "alternatives": [
        {"pattern": "Could you help me", "sentence": "Could you help me...?", "note": "Drop 'to'; 'help someone (do) something'"},
    ]},
    {"trigger": ["i think i can", "i can do this"], "alternatives": [
        {"pattern": "I believe I'm well-suited", "sentence": "I believe I'm well-suited for this role.", "note": "Professional phrasing for interviews"},
    ]},
    # 西语母语常见
    {"trigger": ["depend of", "consist of"], "alternatives": [
        {"pattern": "depend on", "sentence": "It depends on...", "note": "Use 'on' not 'of'"},
    ]},
    {"trigger": ["i have 20 years", "i have years"], "alternatives": [
        {"pattern": "I am X years old", "sentence": "I am 20 years old.", "note": "Use 'to be' not 'to have' for age"},
    ]},
    {"trigger": ["more better", "more fast"], "alternatives": [
        {"pattern": "comparative form", "sentence": "better / faster (no 'more')", "note": "Don't add 'more' to short adjectives"},
    ]},
    {"trigger": ["is available", "is good"], "alternatives": [
        {"pattern": "Is it available", "sentence": "Is it available?", "note": "Include subject 'it' in questions"},
    ]},
    {"trigger": ["you like coffee", "you want"], "alternatives": [
        {"pattern": "Do you like", "sentence": "Do you like coffee?", "note": "Add auxiliary 'do' in questions"},
    ]},
]


def suggest_sentence_patterns(sentence: str, intent: str = "") -> Dict[str, Any]:
    """检测直译/生硬表达，返回地道美式替换建议。"""
    s_lower = sentence.lower().strip()
    matched = []
    for fix in _PATTERN_FIXES:
        for trigger in fix["trigger"]:
            if trigger in s_lower:
                matched.extend(fix["alternatives"])
                break

    # 通用改进建议
    general = []
    if "very" in s_lower and s_lower.count("very") >= 2:
        general.append({"pattern": "intensifier", "sentence": "Use 'really' or a stronger adjective",
                        "note": "Avoid repeating 'very'; e.g., 'exhausted' instead of 'very very tired'"})
    if "i think maybe" in s_lower:
        general.append({"pattern": "hedging", "sentence": "I think... / Maybe...",
                        "note": "Avoid double hedging in professional contexts"})
    matched.extend(general)

    if not matched:
        return {
            "original": sentence,
            "alternatives": [],
            "explanation": "The sentence sounds natural. No major changes needed.",
        }

    # 去重
    seen = set()
    unique = []
    for a in matched:
        key = a["sentence"]
        if key not in seen:
            seen.add(key)
            unique.append(a)

    return {
        "original": sentence,
        "alternatives": unique[:4],
        "explanation": f"Found {len(unique)} suggestion(s) for more natural American English.",
    }
