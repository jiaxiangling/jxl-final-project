# -*- coding: utf-8 -*-
"""课前页：信息收集 → 四维测评 → 雷达图 + 学习路径。"""

import json
import os
from typing import Any, Dict

import streamlit as st

from config import DATA_DIR, L1_LABELS, is_online
from assessment.placement import PlacementAssessor, PlacementResult
from core.state import LearnerProfile
from prompts.system_prompt import build_system_prompt
from tools.curriculum import _load_scenarios
from tools.registry import execute_tool
from visualization.charts import radar_chart, cefr_gauge
from visualization.export import image_download_button
from ui.components import system_prompt_viewer


def render(llm, speech, profile: LearnerProfile) -> None:
    """渲染课前页。"""
    st.header("📚 Pre-Class: Assessment & Planning")

    step = st.session_state.get("pre_step", "info")

    if step == "info":
        _render_info_form(profile)
    elif step == "test":
        _render_assessment(llm, speech, profile)
    elif step == "result":
        _render_result(profile)


def _render_info_form(profile: LearnerProfile) -> None:
    """信息收集表单。"""
    st.subheader("Step 1: Learner Profile")

    with st.form("profile_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Name", value=profile.name, placeholder="Your name")
            l1 = st.selectbox("Native Language", list(L1_LABELS.keys()),
                              format_func=lambda x: L1_LABELS[x],
                              index=list(L1_LABELS.keys()).index(profile.l1) if profile.l1 in L1_LABELS else 0)
            age = st.number_input("Age", 18, 60, value=profile.age or 25)
        with col2:
            occupation = st.text_input("Occupation", value=profile.occupation, placeholder="e.g. Student, Engineer")
            baseline = st.selectbox("Self-assessed English Level",
                                    ["A1", "A2", "B1", "B2", "C1", "C2"],
                                    index=["A1", "A2", "B1", "B2", "C1", "C2"].index(profile.baseline_level) if profile.baseline_level in ["A1", "A2", "B1", "B2", "C1", "C2"] else 2)
            goals = st.multiselect("Learning Goals",
                                   ["daily_life", "workplace", "interview", "exam"],
                                   format_func=lambda x: {"daily_life": "Daily Life", "workplace": "Workplace",
                                                          "interview": "Interview Prep", "exam": "Exam Prep"}[x],
                                   default=profile.goals)

        scenarios = _load_scenarios()
        pain = st.multiselect("Pain Point Scenarios (most needed)",
                              [s["id"] for s in scenarios],
                              format_func=lambda x: next((s["name_zh"] for s in scenarios if s["id"] == x), x),
                              default=profile.pain_scenarios)

        submitted = st.form_submit_button("Start Assessment →", use_container_width=True)

    if submitted:
        profile.name = name
        profile.l1 = l1
        profile.age = age
        profile.occupation = occupation
        profile.baseline_level = baseline
        profile.cefr = baseline
        profile.goals = goals
        profile.pain_scenarios = pain
        st.session_state.profile = profile
        st.session_state.pre_step = "test"
        st.session_state.assessment_answers = {}
        st.rerun()


def _render_assessment(llm, speech, profile: LearnerProfile) -> None:
    """四维测评。"""
    st.subheader("Step 2: English Proficiency Assessment")
    st.caption("Four dimensions: Listening · Speaking · Reading · Writing")

    assessor = PlacementAssessor(llm, speech)
    answers: Dict[str, Any] = st.session_state.get("assessment_answers", {})

    dimensions = ["listening", "reading", "speaking", "writing"]
    dim_labels = {"listening": "🎧 Listening", "reading": "📖 Reading",
                  "speaking": "🎙️ Speaking", "writing": "✍️ Writing"}

    for dim in dimensions:
        st.markdown(f"### {dim_labels[dim]}")
        questions = assessor.get_questions(dim)

        for q in questions:
            qid = q["id"]
            if q["type"] == "mc":
                # 听力：在线模式可播放音频
                if dim == "listening" and speech.available:
                    if st.button(f"🔊 Play audio ({qid})", key=f"play_{qid}"):
                        try:
                            audio = speech.synthesize(q.get("audio_text", q["prompt"]))
                            if audio:
                                st.audio(audio, format="audio/mp3")
                        except Exception:
                            st.warning("Audio playback failed. Read the text below.")
                    st.caption(f"Text: \"{q.get('audio_text', '')}\"")
                else:
                    st.caption(f"Read: {q.get('audio_text', q['prompt'])}")

                selected = st.radio(q["prompt"], range(len(q["options"])),
                                    format_func=lambda i: q["options"][i],
                                    key=f"q_{qid}", index=None)
                if selected is not None:
                    answers[qid] = selected
            else:
                # 开放题
                if dim == "speaking":
                    if speech.available:
                        st.caption(f"🎤 {q['prompt']}")
                        audio_input = st.audio_input(f"Record your answer ({qid})", key=f"audio_{qid}")
                        text_input = st.text_area(f"Or type your answer ({qid})", key=f"text_{qid}",
                                                  height=80, placeholder="Type here if you prefer text...")
                        if audio_input:
                            try:
                                answers[qid] = speech.transcribe(audio_input.getvalue())
                            except Exception:
                                answers[qid] = text_input or ""
                        elif text_input:
                            answers[qid] = text_input
                    else:
                        answers[qid] = st.text_area(q["prompt"], key=f"text_{qid}",
                                                    height=80, placeholder="Type your answer here...")
                else:
                    answers[qid] = st.text_area(q["prompt"], key=f"text_{qid}",
                                                height=80, placeholder="Type your answer here...")

        st.divider()

    st.session_state.assessment_answers = answers

    if st.button("Submit Assessment →", type="primary", use_container_width=True):
        with st.spinner("Evaluating your English level..."):
            result = assessor.assess(profile, answers)
            st.session_state.assessment_result = result
            profile.placement_scores = result.scores
            profile.cefr = result.cefr

            # 调用 plan_learning_path 工具（agentic 特性）
            path_result = execute_tool("plan_learning_path", {
                "profile": {"l1": profile.l1, "goals": profile.goals,
                            "pain_scenarios": profile.pain_scenarios, "cefr": profile.cefr},
                "assessment": {"scores": result.scores, "overall_cefr": result.cefr},
            })
            profile.learning_path = path_result
            st.session_state.learning_path = path_result

        st.session_state.pre_step = "result"
        st.rerun()


def _render_result(profile: LearnerProfile) -> None:
    """测评结果与学习路径。"""
    st.subheader("Step 3: Results & Learning Path")

    result: PlacementResult = st.session_state.get("assessment_result")
    if not result:
        st.warning("No assessment result found. Please complete the assessment first.")
        if st.button("← Back to Assessment"):
            st.session_state.pre_step = "test"
            st.rerun()
        return

    # 雷达图
    col1, col2 = st.columns([3, 2])
    with col1:
        st.plotly_chart(radar_chart(result.scores, result.cefr, profile.l1), use_container_width=True)
        image_download_button(radar_chart(result.scores, result.cefr, profile.l1),
                              filename="assessment_radar.png",
                              label="📥 Download Assessment Chart (PNG)")
    with col2:
        st.plotly_chart(cefr_gauge(result.cefr), use_container_width=True)
        st.markdown(f"**Overall: CEFR {result.cefr}**")
        st.markdown(result.rationale)

    st.divider()

    # 学习路径
    st.subheader("🗺️ Personalized Learning Path")
    path = st.session_state.get("learning_path", profile.learning_path)
    if path and isinstance(path, dict):
        st.markdown(f"**Rationale:** {path.get('rationale', '')}")

        for phase in path.get("phases", []):
            with st.expander(f"📌 {phase.get('name', 'Phase')}", expanded=True):
                st.markdown(f"**Focus:** {phase.get('focus', '')}")
                st.markdown(f"**Scenarios:** {', '.join(phase.get('scenarios', []))}")
                st.markdown(f"**Target CEFR:** {phase.get('target_cefr', '')}")
                st.markdown(f"**Estimated sessions:** {phase.get('est_sessions', '')}")

        milestones = path.get("milestones", [])
        if milestones:
            st.markdown("**Milestones:**")
            for m in milestones:
                st.markdown(f"- *{m.get('after', '')}*: {m.get('goal', '')}")

    st.divider()

    # 系统提示词预览
    system_prompt_viewer(build_system_prompt(profile, None, None, 0))

    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("← Redo Assessment", use_container_width=True):
            st.session_state.pre_step = "test"
            st.session_state.assessment_answers = {}
            st.rerun()
    with col_b:
        if st.button("Start Practicing →", type="primary", use_container_width=True):
            st.session_state.stage = "in_class"
            st.rerun()
