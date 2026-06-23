# -*- coding: utf-8 -*-
"""词典与音标工具：lookup_word / get_phonetics / expand_examples。"""

import json
import os
from typing import Any, Dict

from config import TOOLS_DATA_DIR

_WORD_DICT: Dict[str, Any] = {}


def _load_word_dict() -> Dict[str, Any]:
    global _WORD_DICT
    if not _WORD_DICT:
        path = os.path.join(TOOLS_DATA_DIR, "word_dict.json")
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                _WORD_DICT = json.load(f)
    return _WORD_DICT


def lookup_word(word: str, context: str = "") -> Dict[str, Any]:
    """查询单词释义。优先本地词典，未命中返回提示。"""
    w = word.lower().strip()
    wd = _load_word_dict()
    if w in wd:
        entry = wd[w]
        return {
            "word": w,
            "pos": entry.get("pos", ""),
            "definitions": entry.get("definitions", []),
            "ipa": entry.get("ipa", ""),
            "examples": entry.get("examples", []),
            "cefr_level": entry.get("cefr", ""),
            "source": "local_dict",
        }
    # 未命中：返回基本结构，提示 LLM 可自行补充
    return {
        "word": w,
        "pos": "",
        "definitions": [f"(Not in offline dictionary) The LLM should define '{w}' based on context."],
        "ipa": "",
        "examples": [],
        "cefr_level": "",
        "source": "not_found",
        "hint": f"'{w}' not found in local dict. If online, the LLM can provide a definition.",
    }


def get_phonetics(word: str) -> Dict[str, Any]:
    """返回美式音标。优先本地词典。"""
    w = word.lower().strip()
    wd = _load_word_dict()
    if w in wd and wd[w].get("ipa"):
        ipa = wd[w]["ipa"]
        return {
            "word": w,
            "ipa_us": ipa,
            "syllables": _count_syllables(w),
            "stress": "primary",
            "similar_sounding": _similar_sounds(w),
            "source": "local_dict",
        }
    return {
        "word": w,
        "ipa_us": f"(unknown — LLM may provide IPA for '{w}')",
        "syllables": _count_syllables(w),
        "stress": "primary",
        "similar_sounding": [],
        "source": "estimated",
    }


def expand_examples(phrase: str, count: int = 3) -> Dict[str, Any]:
    """为短语生成例句。本地词典有则用，否则返回模板提示。"""
    p = phrase.lower().strip()
    wd = _load_word_dict()
    examples = []
    if p in wd:
        examples = wd[p].get("examples", [])[:count]
    # 补充通用模板例句
    if len(examples) < count:
        templates = [
            f"Could you use '{phrase}' in a sentence for me?",
            f"I heard '{phrase}' in a conversation — what does it mean in context?",
            f"Let me practice saying '{phrase}'.",
        ]
        for t in templates:
            if len(examples) < count:
                examples.append(t)
    return {"phrase": phrase, "examples": examples[:count]}


def _count_syllables(word: str) -> int:
    vowels = "aeiouy"
    count = 0
    prev_vowel = False
    for ch in word:
        is_vowel = ch in vowels
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    return max(count, 1)


def _similar_sounds(word: str) -> list:
    """返回容易混淆的音（简化版）。"""
    pairs = {
        "think": ["sink", "tink"], "that": ["dat", "zat"],
        "very": ["berry", "wery"], "right": ["light"],
        "beach": ["bitch"], "ship": ["chip"], "zoo": ["soo"],
    }
    return pairs.get(word, [])
