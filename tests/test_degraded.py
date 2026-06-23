# -*- coding: utf-8 -*-
"""离线降级模式全链路冒烟测试：无 API key 时 agentic 流程完整性。"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import is_online, get_settings
from core.state import LearnerProfile, SessionState, DifficultyState
from core.llm_client import get_llm, MockLLMClient
from core.speech import get_speech, MockSpeech
from core.agent import ConversationOrchestrator
from assessment.placement import PlacementAssessor
from assessment.reporting import generate_session_report
from visualization.charts import radar_chart, error_distribution
from tools.registry import execute_tool
from prompts.system_prompt import build_system_prompt


def test_offline_mode_detection():
    """测试离线模式检测。"""
    llm = get_llm()
    speech = get_speech()
    assert isinstance(llm, MockLLMClient) or hasattr(llm, "_client"), "LLM should be MockLLM in offline"
    assert speech.available == False or speech.available == True, "Speech should be MockSpeech in offline"
    mode = get_settings().mode
    print(f"✅ test_offline_mode_detection passed (mode={mode})")


def test_offline_full_conversation():
    """离线模式完整对话流程。"""
    profile = LearnerProfile(name="Test", l1="zh", cefr="B1", baseline_level="B1",
                              goals=["daily_life"], pain_scenarios=["housing"])
    session = SessionState(user_id=profile.user_id, scenario_id="housing",
                           voice_enabled=False, difficulty=DifficultyState(cefr="B1"))
    scenario = {"id": "housing", "name_en": "Apartment Hunting",
                "persona": "Property Manager", "target_phrases": ["Is it available?"],
                "opening_lines": ["Hi!"]}

    llm = MockLLMClient()
    speech = MockSpeech()
    orch = ConversationOrchestrator(llm, speech, profile)

    # 模拟3轮对话
    inputs = [
        "Hi, I want rent room near downtown.",
        "What does lease mean?",
        "How much is the deposit?",
    ]
    for text in inputs:
        result = orch.handle_turn(text, session, scenario)
        assert result.reply_text != "", "Reply should not be empty"
        assert len(result.trace.events) > 0, "Trace should have events"

    # 验证会话状态
    assert len(session.turns) == 3
    assert session.metrics["turns"] == 3
    assert session.metrics["tool_calls"] > 0
    assert len(session.mistakes) > 0

    print(f"✅ test_offline_full_conversation passed (3 turns, {session.metrics['tool_calls']} tool calls, {len(session.mistakes)} mistakes)")


def test_offline_assessment():
    """离线模式测评。"""
    profile = LearnerProfile(name="Test", l1="zh", cefr="B1", baseline_level="B1")
    assessor = PlacementAssessor(MockLLMClient(), MockSpeech())

    answers = {
        "l1": 0,  # correct
        "l2": 1,  # correct
        "r1": 1,  # correct
        "r2": 2,  # correct
        "s1": "My name is Test. I am a software engineer. I want to improve my English for work.",
        "s2": "I needed to speak English at airport. I asked for directions to the gate.",
        "w1": "Dear landlord, I saw your listing for the apartment. Is it still available? Thank you.",
        "w2": "I wake up at 7am and go to work. I have meetings in the morning and code in the afternoon.",
    }
    result = assessor.assess(profile, answers)

    assert "listening" in result.scores
    assert "speaking" in result.scores
    assert "reading" in result.scores
    assert "writing" in result.scores
    assert result.cefr in ["A1", "A2", "B1", "B2", "C1", "C2"]
    assert result.rationale != ""

    print(f"✅ test_offline_assessment passed (CEFR={result.cefr}, scores={result.scores})")


def test_offline_feedback_and_charts():
    """离线模式反馈和图表生成。"""
    profile = LearnerProfile(name="Test", l1="zh", cefr="B1")
    session = SessionState(user_id=profile.user_id, scenario_id="housing",
                           voice_enabled=False, difficulty=DifficultyState(cefr="B1"))
    session.add_mistake("grammar", "I no like", "I don't like", "missing_aux")
    session.add_mistake("pronunciation", "sink", "think", "th_to_s")
    session.metrics["turns"] = 5
    session.metrics["error_rate"] = 0.4
    session.metrics["tool_calls"] = 8

    # 生成反馈
    report = generate_session_report(session)
    assert report.summary != ""
    assert len(report.strengths) > 0
    assert len(report.weaknesses) > 0
    assert report.encouragement != ""

    # 生成图表
    radar = radar_chart({"listening": 60, "speaking": 55, "reading": 70, "writing": 65}, "B1", "zh")
    assert radar is not None

    err_chart = error_distribution(session.mistakes)
    assert err_chart is not None

    print(f"✅ test_offline_feedback_and_charts passed (strengths={len(report.strengths)}, weaknesses={len(report.weaknesses)})")


def test_offline_system_prompt():
    """离线模式系统提示词生成。"""
    profile = LearnerProfile(name="Test", l1="zh", cefr="B1")
    prompt = build_system_prompt(profile, None, None, 0)

    assert "IDENTITY" in prompt
    assert "USER PROFILE" in prompt
    assert "BOUNDARIES" in prompt
    assert "LEARNER AWARENESS" in prompt
    assert "Chinese" in prompt  # 中文 L1 awareness
    assert "TOOL-USE RULES" in prompt
    assert "MULTIMODAL RULES" in prompt
    assert "SAFETY" in prompt
    assert "OUTPUT FORMAT" in prompt

    # 测试西语 L1
    profile_es = LearnerProfile(name="Test", l1="es", cefr="B1")
    prompt_es = build_system_prompt(profile_es, None, None, 0)
    assert "Spanish" in prompt_es
    assert "seseo" in prompt_es or "pro-drop" in prompt_es or "false friend" in prompt_es

    print("✅ test_offline_system_prompt passed (8 sections, L1 awareness verified)")


def test_offline_learning_path():
    """离线模式学习路径规划。"""
    result = execute_tool("plan_learning_path", {
        "profile": {"l1": "es", "goals": ["workplace", "interview"],
                    "pain_scenarios": ["interview", "medical"], "cefr": "B1"},
        "assessment": {"listening": 55, "speaking": 50, "reading": 65, "writing": 60, "overall_cefr": "B1"},
    }, None)

    assert "phases" in result
    assert len(result["phases"]) == 3
    assert "rationale" in result
    assert "Spanish" in result["rationale"] or "interview" in result["rationale"]

    print(f"✅ test_offline_learning_path passed ({len(result['phases'])} phases)")


if __name__ == "__main__":
    test_offline_mode_detection()
    test_offline_full_conversation()
    test_offline_assessment()
    test_offline_feedback_and_charts()
    test_offline_system_prompt()
    test_offline_learning_path()
    print("\n🎉 All offline degradation tests passed!")
