# -*- coding: utf-8 -*-
"""Agent 编排器测试：ReAct 循环、工具调用、状态更新、trace 完整性。"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.state import LearnerProfile, SessionState, DifficultyState
from core.llm_client import MockLLMClient, LLMResponse, ToolCall
from core.speech import MockSpeech
from core.agent import ConversationOrchestrator, parse_reply
from core.trace import TraceCollector


def _make_orchestrator():
    """创建测试用编排器（离线模式）。"""
    profile = LearnerProfile(name="Test", l1="zh", cefr="B1", baseline_level="B1")
    session = SessionState(
        user_id=profile.user_id, scenario_id="housing",
        voice_enabled=False, difficulty=DifficultyState(cefr="B1"),
    )
    scenario = {
        "id": "housing", "name_en": "Apartment Hunting",
        "persona": "Property Manager", "target_phrases": ["Is it available?"],
        "opening_lines": ["Hi!"],
    }
    orch = ConversationOrchestrator(MockLLMClient(), MockSpeech(), profile)
    return orch, profile, session, scenario


def test_handle_turn_basic():
    """测试单轮对话基本流程。"""
    orch, profile, session, scenario = _make_orchestrator()
    result = orch.handle_turn("Hi, I want rent room.", session, scenario)

    assert result.user_text == "Hi, I want rent room."
    assert result.reply_text != ""
    assert len(result.tools_used) > 0
    assert len(result.trace.events) > 0
    assert len(session.turns) == 1
    print(f"✅ test_handle_turn_basic passed (tools={len(result.tools_used)}, trace={len(result.trace.events)})")


def test_tool_calls_recorded():
    """测试工具调用被正确记录。"""
    orch, profile, session, scenario = _make_orchestrator()
    result = orch.handle_turn("What does lease mean?", session, scenario)

    tool_names = [t["name"] for t in result.tools_used]
    assert "lookup_word" in tool_names or "assess_pronunciation" in tool_names
    assert "get_phonetics" in tool_names or "assess_pronunciation" in tool_names
    print(f"✅ test_tool_calls_recorded passed (tools: {tool_names})")


def test_mistakes_logged():
    """测试错误被记录到 session。"""
    orch, profile, session, scenario = _make_orchestrator()
    result = orch.handle_turn("I no like this apartment.", session, scenario)

    assert len(result.mistakes_logged) > 0
    assert len(session.mistakes) > 0
    assert session.mistakes[0]["category"] == "grammar"
    print(f"✅ test_mistakes_logged passed (mistakes: {len(session.mistakes)})")


def test_trace_decision_summary():
    """测试 trace 决策摘要生成。"""
    orch, profile, session, scenario = _make_orchestrator()
    result = orch.handle_turn("Hello, I want rent room.", session, scenario)

    summary = result.trace.decision_summary()
    assert "本轮自主决策" in summary
    print(f"✅ test_trace_decision_summary passed ({summary})")


def test_parse_reply():
    """测试回复解析。"""
    parsed = parse_reply("[CORRECTION]\nold -> new\n[REPLY]\nHello there!\n[HINT]\nTip here")
    assert parsed["correction"] == "old -> new"
    assert parsed["reply"] == "Hello there!"
    assert parsed["hint"] == "Tip here"
    print("✅ test_parse_reply passed")


def test_parse_reply_no_markers():
    """测试无标记的回复解析。"""
    parsed = parse_reply("Just a plain reply.")
    assert parsed["reply"] == "Just a plain reply."
    print("✅ test_parse_reply_no_markers passed")


def test_multi_turn_session():
    """测试多轮对话。"""
    orch, profile, session, scenario = _make_orchestrator()

    inputs = [
        "Hi, I want rent room near downtown.",
        "What does lease mean?",
        "How much is the deposit?",
    ]
    for i, text in enumerate(inputs):
        result = orch.handle_turn(text, session, scenario)
        assert len(session.turns) == i + 1
        assert result.reply_text != ""

    assert len(session.turns) == 3
    assert session.metrics["turns"] == 3
    print(f"✅ test_multi_turn_session passed (3 turns, {session.metrics['tool_calls']} tool calls)")


def test_audio_none_offline():
    """测试离线模式下无音频。"""
    orch, profile, session, scenario = _make_orchestrator()
    result = orch.handle_turn("Hello", session, scenario)
    assert result.reply_audio is None
    print("✅ test_audio_none_offline passed")


def test_difficulty_change():
    """测试难度调整（第3轮触发）。"""
    orch, profile, session, scenario = _make_orchestrator()

    # 前2轮
    for text in ["Hello there", "I want to rent a room"]:
        orch.handle_turn(text, session, scenario)

    # 第3轮应触发 adjust_difficulty
    result = orch.handle_turn("How much is the deposit?", session, scenario)
    tool_names = [t["name"] for t in result.tools_used]
    assert "adjust_difficulty" in tool_names, f"Expected adjust_difficulty in {tool_names}"
    print(f"✅ test_difficulty_change passed (tools: {tool_names})")


if __name__ == "__main__":
    test_handle_turn_basic()
    test_tool_calls_recorded()
    test_mistakes_logged()
    test_trace_decision_summary()
    test_parse_reply()
    test_parse_reply_no_markers()
    test_multi_turn_session()
    test_audio_none_offline()
    test_difficulty_change()
    print("\n🎉 All agent tests passed!")
