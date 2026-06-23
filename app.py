# -*- coding: utf-8 -*-
"""SpeakEasy — AI 英语口语陪练自主智能体系统。

Streamlit 入口：侧边栏导航 + 三阶段路由 + 全局状态管理。
"""

import streamlit as st

from config import get_settings, is_online, ensure_dirs, L1_LABELS
from core.llm_client import get_llm
from core.speech import get_speech
from core.agent import ConversationOrchestrator
from core.state import LearnerProfile
from prompts.system_prompt import build_system_prompt
from ui.styles import inject_styles
from ui.components import render_feature_badges, mode_badge, system_prompt_viewer
from pages import pre_class, in_class, post_class


def main() -> None:
    st.set_page_config(
        page_title="SpeakEasy — AI English Coach",
        page_icon="🗣️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    ensure_dirs()
    inject_styles()
    _init_state()

    # ── 顶部 ──
    st.title("🗣️ SpeakEasy — AI English Speaking Coach")
    st.caption("Agentic AI system for Chinese & Spanish (Mexican) speakers · "
               "Real-life American English practice")
    render_feature_badges()
    mode_badge("online" if is_online() else "offline")

    # ── 侧边栏 ──
    _render_sidebar()

    # ── 页面分发 ──
    stage = st.session_state.get("stage", "pre_class")
    llm = get_llm()
    speech = get_speech()
    profile: LearnerProfile = st.session_state.profile

    if stage == "pre_class":
        pre_class.render(llm, speech, profile)
    elif stage == "in_class":
        orchestrator = ConversationOrchestrator(llm, speech, profile)
        in_class.render(orchestrator, speech, profile)
    elif stage == "post_class":
        post_class.render(profile)


def _init_state() -> None:
    """初始化全局 session_state。"""
    if "profile" not in st.session_state:
        st.session_state.profile = LearnerProfile()
    if "stage" not in st.session_state:
        st.session_state.stage = "pre_class"
    if "pre_step" not in st.session_state:
        st.session_state.pre_step = "info"


def _render_sidebar() -> None:
    """渲染侧边栏。"""
    profile: LearnerProfile = st.session_state.profile

    with st.sidebar:
        st.markdown("### 🗣️ SpeakEasy")
        st.caption("AI English Speaking Coach")

        # 阶段切换
        stages = ["pre_class", "in_class", "post_class"]
        stage_labels = {"pre_class": "📚 Pre-Class (Assessment)",
                        "in_class": "🗣️ In-Class (Practice)",
                        "post_class": "📊 Post-Class (Feedback)"}
        current = st.session_state.get("stage", "pre_class")
        selected = st.radio("Navigation", stages,
                            format_func=lambda x: stage_labels[x],
                            index=stages.index(current) if current in stages else 0,
                            key="nav_stage")
        if selected != current:
            st.session_state.stage = selected
            st.rerun()

        st.divider()

        # 用户信息卡
        st.markdown("### 👤 Learner Profile")
        if profile.name:
            st.markdown(f"**Name:** {profile.name}")
        st.markdown(f"**L1:** {L1_LABELS.get(profile.l1, profile.l1)}")
        st.markdown(f"**CEFR:** {profile.cefr}")
        if profile.goals:
            goal_labels = {"daily_life": "Daily Life", "workplace": "Workplace",
                           "interview": "Interview", "exam": "Exam"}
            st.markdown(f"**Goals:** {', '.join(goal_labels.get(g, g) for g in profile.goals)}")

        st.divider()

        # 设置
        st.markdown("### ⚙️ Settings")
        settings = get_settings()
        st.markdown(f"**LLM:** `{settings.llm_model}`")
        st.markdown(f"**STT:** `Whisper`")
        st.markdown(f"**TTS:** `{settings.tts_model}` / `{settings.tts_voice}`")
        st.markdown(f"**Max tool iters:** {settings.max_tool_iters}")

        st.divider()

        # 系统提示词查看器（特性④）
        st.markdown("### 📝 System Prompt Architecture")
        st.caption("Click below to view the structured system prompt "
                   "(role, boundaries, L1 awareness, rules, safety).")
        system_prompt_viewer(build_system_prompt(profile, None, None, 0))

        st.divider()

        # 4特性导览
        st.markdown("### 🗺️ Feature Map")
        st.markdown("""
        - **🤖 Agentic Workflow** → In-Class: Agent Trace panel
        - **🔧 Function Calling** → In-Class: Tool Call cards
        - **📊 Multimodal** → Pre-Class: Radar chart · In-Class: Voice · Post-Class: Dashboard
        - **📝 System Prompt** → This sidebar (expand above)
        """)


if __name__ == "__main__":
    main()
