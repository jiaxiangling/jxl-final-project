# -*- coding: utf-8 -*-
"""课中页：语音对话 + ReAct trace + 工具调用 + 难度自适应（评分主舞台）。"""

import base64
import html
from typing import Any, Dict, Optional

import streamlit as st

from config import is_online
from core.agent import ConversationOrchestrator, TurnResult, parse_reply
from core.state import SessionState, DifficultyState
from core.trace import TraceCollector, TraceEvent
from tools.curriculum import _load_scenarios
from ui.components import (
    workflow_diagram, difficulty_indicator, agent_trace_panel,
    render_chat_message, tool_summary_card, render_tool_usage_sidebar,
)


def render(orchestrator: ConversationOrchestrator, speech, profile) -> None:
    """渲染课中页。"""
    st.header("🗣️ In-Class: Conversation Practice")

    # 场景选择
    scenario = st.session_state.get("scenario")
    if not scenario:
        _render_scenario_selection()
        return

    # 初始化 / 重置 session
    session = st.session_state.get("session")
    if (not session or session.scenario_id != scenario["id"]
            or st.session_state.get("reset_session")):
        session = SessionState(
            user_id=profile.user_id,
            scenario_id=scenario["id"],
            voice_enabled=speech.available,
            difficulty=DifficultyState(cefr=profile.cefr),
        )
        st.session_state.session = session
        st.session_state.reset_session = False
        st.session_state.last_turn_result = None

    # ── 处理待处理输入 ──
    pending = st.session_state.pop("_pending_input", None)
    if pending is not None:
        with st.status("Agent processing...", expanded=True) as status:
            try:
                result = orchestrator.handle_turn(pending, session, scenario)
                st.session_state.last_turn_result = result
                session.save()
                status.update(label="Agent completed", state="complete")
            except Exception as e:
                status.update(label=f"Error: {e}", state="error")

    # ── 顶部：工作流图 + 难度 ──
    workflow_diagram()
    last_result: Optional[TurnResult] = st.session_state.get("last_turn_result")
    difficulty_indicator(
        session.difficulty.cefr,
        last_result.difficulty_change if last_result else None,
    )

    st.divider()

    # ── 场景信息 ──
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**{scenario.get('icon', '')} {scenario.get('name_en', '')}** "
                     f"— {scenario.get('description', '')}")
        st.caption(f"Persona: {scenario.get('persona', 'N/A')} | "
                    f"Target phrases: {', '.join(scenario.get('target_phrases', [])[:2])}")
    with col2:
        if st.button("🔄 Change Scenario"):
            st.session_state.scenario = None
            st.session_state.reset_session = True
            st.rerun()

    # ── 对话历史 ──
    st.subheader("💬 Conversation")
    latest_turn_idx = len(session.turns) - 1
    for turn_idx, turn in enumerate(session.turns):
        with st.chat_message("user"):
            st.markdown(turn.user_text)
        with st.chat_message("assistant"):
            parsed = parse_reply(turn.assistant_text)
            # 把当前消息的所有 HTML 块拼成一个，一次性渲染，避免多次 unsafe_allow_html 触发 DOM 冲突
            html_parts = []
            if parsed.get("correction"):
                html_parts.append(
                    f'<div class="correction-block">📝 <strong>Correction:</strong><br>'
                    f'{html.escape(parsed["correction"])}</div>')
            if parsed.get("hint"):
                html_parts.append(
                    f'<div class="hint-block">💡 {html.escape(parsed["hint"])}</div>')
            if html_parts:
                st.markdown("".join(html_parts), unsafe_allow_html=True)
            if parsed.get("reply"):
                st.markdown(parsed["reply"])
            # 只播放最新一轮的音频，用原生 HTML audio 标签规避 st.audio DOM 冲突
            if turn.assistant_audio and turn_idx == latest_turn_idx:
                b64 = base64.b64encode(turn.assistant_audio).decode("utf-8")
                st.markdown(
                    f'<audio controls autoplay style="width:100%" '
                    f'src="data:audio/mp3;base64,{b64}"></audio>',
                    unsafe_allow_html=True,
                )

    # ── 最近一轮 Trace ──
    if last_result:
        st.markdown("---")
        st.subheader("🤖 Agent Workflow Trace")
        st.caption("This panel shows the AI's autonomous decision-making process "
                   "(Thought → Tool Call → Observation → Reply).")
        agent_trace_panel(last_result.trace)
        tool_summary_card(last_result.tools_used)

    # ── 输入区 ──
    st.markdown("---")
    st.subheader("🎤 Your Turn")

    col_text, col_send = st.columns([4, 1])
    with col_text:
        text_input = st.text_input("Type in English:", key="text_input",
                                   placeholder="Type your message and press Send...",
                                   label_visibility="collapsed")
    with col_send:
        send_btn = st.button("📤 Send", use_container_width=True)

    audio_input = None
    if speech.available:
        st.caption("🎙️ Or record your voice:")
        audio_input = st.audio_input("Record", key="audio_input")

    # 处理发送
    if send_btn and text_input.strip():
        st.session_state._pending_input = text_input.strip()
        st.rerun()
    elif audio_input:
        st.session_state._pending_input = audio_input.getvalue()
        st.rerun()

    # ── 侧栏：工具使用统计 ──
    all_tools = []
    for t in session.turns:
        all_tools.extend(t.tool_invocations)
    if all_tools:
        with st.sidebar:
            render_tool_usage_sidebar(all_tools)
            st.markdown(f"**Total tool calls:** {len(all_tools)}")
            st.markdown(f"**Mistakes logged:** {len(session.mistakes)}")
            st.markdown(f"**Vocab learned:** {len(session.vocab)}")

    # ── 结束练习 ──
    st.markdown("---")
    if st.button("🏁 End Session & View Feedback", type="primary", use_container_width=True):
        if session.turns:
            session.ended_at = _now_str()
            session.save()
        st.session_state.stage = "post_class"
        st.rerun()


def _render_scenario_selection() -> None:
    """场景选择网格。"""
    st.subheader("Select a Practice Scenario")
    st.caption("Choose a real-life situation to practice your English speaking skills.")

    scenarios = _load_scenarios()
    cols = st.columns(4)
    for i, sc in enumerate(scenarios):
        with cols[i % 4]:
            icon = sc.get("icon", "💬")
            if st.button(f"{icon}\n{sc.get('name_zh', sc['id'])}\n{sc.get('name_en', '')}",
                         key=f"sc_{sc['id']}", use_container_width=True,
                         help=sc.get("description", "")):
                st.session_state.scenario = sc
                st.rerun()

    st.divider()
    if st.button("💬 Free Conversation (no specific scenario)", use_container_width=True):
        st.session_state.scenario = {
            "id": "free", "name_en": "Free Conversation", "name_zh": "自由对话",
            "description": "Open conversation practice", "persona": "Friendly Chat Partner",
            "target_phrases": [], "opening_lines": ["Hi! What would you like to talk about today?"],
        }
        st.rerun()


def _now_str() -> str:
    from datetime import datetime
    return datetime.now().isoformat(timespec="seconds")
