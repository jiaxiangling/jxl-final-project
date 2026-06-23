# -*- coding: utf-8 -*-
"""工具集单元测试：验证每个工具的入参/返回。"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.dictionary import lookup_word, get_phonetics, expand_examples
from tools.patterns import suggest_sentence_patterns
from tools.pronunciation import assess_pronunciation
from tools.difficulty import adjust_difficulty
from tools.curriculum import get_scenario_curriculum, plan_learning_path
from tools.feedback import log_mistake, generate_session_feedback
from tools.registry import execute_tool, get_schemas, get_tool_names


def test_lookup_word():
    """测试单词查询。"""
    result = lookup_word("lease")
    assert result["word"] == "lease"
    assert "definitions" in result
    assert len(result["definitions"]) > 0
    assert result["ipa"] == "/liːs/"
    print("✅ test_lookup_word passed")


def test_lookup_word_not_found():
    """测试未收录词。"""
    result = lookup_word("xyzabc")
    assert result["source"] == "not_found"
    print("✅ test_lookup_word_not_found passed")


def test_get_phonetics():
    """测试音标查询。"""
    result = get_phonetics("deposit")
    assert "ipa_us" in result
    assert "syllables" in result
    assert result["syllables"] >= 1
    print("✅ test_get_phonetics passed")


def test_assess_pronunciation_zh():
    """测试中文 L1 发音错误检测。"""
    result = assess_pronunciation("I think you are right, very good", "zh")
    assert "issues" in result
    assert "score" in result
    assert 0 <= result["score"] <= 100
    assert "tips" in result
    print(f"✅ test_assess_pronunciation_zh passed (score={result['score']}, issues={len(result['issues'])})")


def test_assess_pronunciation_es():
    """测试西语 L1 发音错误检测。"""
    result = assess_pronunciation("I went to the soo yesterday, it depends of the weather", "es")
    assert "issues" in result
    assert result["learner_l1"] == "es"
    print(f"✅ test_assess_pronunciation_es passed (issues={len(result['issues'])})")


def test_adjust_difficulty_lower():
    """测试高错误率降级。"""
    result = adjust_difficulty("B2", {"fluency": 2.0, "error_rate": 0.6, "turns": 5})
    assert result["new_cefr"] == "B1"
    assert result["changed"] is True
    print(f"✅ test_adjust_difficulty_lower passed (B2→{result['new_cefr']})")


def test_adjust_difficulty_raise():
    """测试低错误率升级。"""
    result = adjust_difficulty("B1", {"fluency": 4.5, "error_rate": 0.05, "turns": 4})
    assert result["new_cefr"] == "B2"
    assert result["changed"] is True
    print(f"✅ test_adjust_difficulty_raise passed (B1→{result['new_cefr']})")


def test_suggest_sentence_patterns():
    """测试句型替换。"""
    result = suggest_sentence_patterns("I want rent room")
    assert "alternatives" in result
    assert len(result["alternatives"]) > 0
    print(f"✅ test_suggest_sentence_patterns passed ({len(result['alternatives'])} suggestions)")


def test_get_scenario_curriculum():
    """测试场景课程获取。"""
    result = get_scenario_curriculum("housing", "B1")
    assert result["scenario"]["id"] == "housing"
    assert "objectives" in result
    assert len(result["objectives"]) > 0
    print(f"✅ test_get_scenario_curriculum passed")


def test_plan_learning_path():
    """测试学习路径规划。"""
    result = plan_learning_path(
        {"l1": "zh", "goals": ["workplace"], "pain_scenarios": ["interview"], "cefr": "B1"},
        {"listening": 60, "speaking": 55, "reading": 70, "writing": 65, "overall_cefr": "B1"},
    )
    assert "phases" in result
    assert len(result["phases"]) == 3
    assert "rationale" in result
    print(f"✅ test_plan_learning_path passed ({len(result['phases'])} phases)")


def test_log_mistake():
    """测试错误记录。"""
    result = log_mistake("grammar", "I no like", "I don't like", "Missing auxiliary")
    assert result["logged"] is True
    assert result["category"] == "grammar"
    print("✅ test_log_mistake passed")


def test_execute_tool_dispatch():
    """测试工具分发。"""
    result = execute_tool("lookup_word", {"word": "lease"}, None)
    assert result["word"] == "lease"
    result = execute_tool("unknown_tool", {}, None)
    assert "error" in result
    print("✅ test_execute_tool_dispatch passed")


def test_registry_schemas():
    """测试 schema 导出。"""
    schemas = get_schemas()
    names = get_tool_names()
    assert len(schemas) == 10
    assert len(names) == 10
    assert "lookup_word" in names
    assert "assess_pronunciation" in names
    assert "adjust_difficulty" in names
    print(f"✅ test_registry_schemas passed ({len(schemas)} tools)")


if __name__ == "__main__":
    test_lookup_word()
    test_lookup_word_not_found()
    test_get_phonetics()
    test_assess_pronunciation_zh()
    test_assess_pronunciation_es()
    test_adjust_difficulty_lower()
    test_adjust_difficulty_raise()
    test_suggest_sentence_patterns()
    test_get_scenario_curriculum()
    test_plan_learning_path()
    test_log_mistake()
    test_execute_tool_dispatch()
    test_registry_schemas()
    print("\n🎉 All tool tests passed!")
