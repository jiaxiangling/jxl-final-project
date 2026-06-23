# -*- coding: utf-8 -*-
"""可复用 UI 组件：徽章 / trace 面板 / 聊天气泡 / 工具卡 / 工作流图 / 提示词查看器。"""

import html
import json
from typing import Any, Dict, List, Optional

import streamlit as st

from core.trace import TraceCollector


def render_feature_badges() -> None:
    """顶部 4 特性徽章。"""
    st.markdown("""
    <div>
        <span class="feature-badge badge-agentic">🤖 Agentic Workflow</span>
        <span class="feature-badge badge-tools">🔧 Function Calling</span>
        <span class="feature-badge badge-multimodal">📊 Multimodal</span>
        <span class="feature-badge badge-prompt">📝 System Prompt</span>
    </div>
    """, unsafe_allow_html=True)


def mode_badge(mode: str) -> None:
    """模式徽章：在线 🟢 / 离线 🟡。"""
    if mode == "online":
        st.markdown(
            '<span class="mode-badge mode-online">🟢 Online (GPT-4o + Whisper + TTS)</span>',
            unsafe_allow_html=True)
    else:
        st.markdown(
            '<span class="mode-badge mode-offline">🟡 Offline Demo (MockLLM — text only, voice disabled)</span>',
            unsafe_allow_html=True)


def workflow_diagram() -> None:
    """静态 ReAct 工作流图。"""
    st.markdown("""
    <div style="padding:8px 0;">
        <span class="workflow-step">🎙️ User Voice</span>
        <span class="workflow-arrow">→</span>
        <span class="workflow-step">Whisper STT</span>
        <span class="workflow-arrow">→</span>
        <span class="workflow-step">💭 Thought</span>
        <span class="workflow-arrow">→</span>
        <span class="workflow-step">🔧 Tool Call</span>
        <span class="workflow-arrow">→</span>
        <span class="workflow-step">📋 Observation</span>
        <span class="workflow-arrow">↻</span>
        <span class="workflow-step">💬 Reply</span>
        <span class="workflow-arrow">→</span>
        <span class="workflow-step">🔊 TTS</span>
    </div>
    """, unsafe_allow_html=True)


def difficulty_indicator(level: str, change: Optional[Dict] = None) -> None:
    """难度指示器。"""
    text = f"📊 CEFR: {level}"
    if change:
        text += f" (adjusted: {change.get('from')} → {change.get('to')})"
    st.markdown(f'<span class="difficulty-indicator">{text}</span>', unsafe_allow_html=True)


def agent_trace_panel(trace: TraceCollector) -> None:
    """渲染 Agent 决策轨迹面板。"""
    if not trace.events:
        st.info("Agent trace will appear here during conversation.")
        return

    # 决策摘要条
    summary = trace.decision_summary()
    st.markdown(f'<div class="decision-summary">{summary}</div>', unsafe_allow_html=True)

    # 事件列表
    for event in trace.events:
        icon = trace.ICONS.get(event.kind, "•")
        css_class = {
            "thought": "trace-thought", "tool_call": "trace-tool",
            "tool_result": "trace-result", "final": "trace-final",
            "difficulty": "trace-difficulty", "stt": "trace-stt", "tts": "trace-stt",
            "safety": "trace-safety",
        }.get(event.kind, "trace-thought")

        detail_html = ""
        if event.detail:
            detail_html = f"<div style='font-size:12px;color:#64748b;margin-top:2px;'>{html.escape(event.detail[:200])}</div>"

        ms_html = ""
        if event.duration_ms:
            ms_html = f" <span style='font-size:11px;color:#94a3b8;'>({event.duration_ms}ms)</span>"

        st.markdown(
            f'<div class="trace-event {css_class}">'
            f'{icon} <strong>Step {event.step}: {html.escape(event.title)}</strong>{ms_html}'
            f'{detail_html}</div>',
            unsafe_allow_html=True
        )


def render_chat_message(role: str, text: str, audio: Optional[bytes] = None,
                        parsed: Optional[Dict[str, str]] = None) -> None:
    """渲染聊天气泡（含纠错高亮和音频播放）。"""
    with st.chat_message(role):
        if parsed:
            # 纠错块
            if parsed.get("correction"):
                st.markdown(f'<div class="correction-block">📝 <strong>Correction:</strong><br>{html.escape(parsed["correction"])}</div>',
                            unsafe_allow_html=True)
            # 主回复
            if parsed.get("reply"):
                st.markdown(parsed["reply"])
            # 提示
            if parsed.get("hint"):
                st.markdown(f'<div class="hint-block">💡 {html.escape(parsed["hint"])}</div>',
                            unsafe_allow_html=True)
        else:
            st.markdown(text)

        # 音频播放
        if audio:
            st.audio(audio, format="audio/mp3")


def system_prompt_viewer(prompt: str) -> None:
    """系统提示词查看器（按 === 分节折叠）。"""
    sections = prompt.split("=== ")
    with st.expander("📝 View System Prompt Architecture", expanded=False):
        st.caption("This is the complete system prompt that defines the AI coach's role, boundaries, rules, and safety constraints.")
        for section in sections:
            if not section.strip():
                continue
            # 提取节标题
            parts = section.split(" ===", 1)
            title = parts[0].strip()
            body = parts[1].strip() if len(parts) > 1 else ""
            if title:
                with st.expander(f"📌 {title}", expanded=False):
                    st.text(body[:2000] + ("..." if len(body) > 2000 else ""))


def tool_summary_card(tools_used: List[Dict[str, Any]]) -> None:
    """本轮工具调用汇总卡。"""
    if not tools_used:
        return
    st.markdown("#### 🔧 Tool Calls This Turn")
    for t in tools_used:
        name = t.get("name", "?")
        args = t.get("arguments", {})
        result = t.get("result", {})
        with st.expander(f"🔧 {name}", expanded=False):
            st.json({"arguments": args, "result": result})


def scenario_grid(scenarios: List[Dict[str, Any]]) -> None:
    """场景卡片网格。"""
    cols = st.columns(4)
    for i, sc in enumerate(scenarios):
        with cols[i % 4]:
            icon = sc.get("icon", "💬")
            name = sc.get("name_zh", sc.get("id", ""))
            name_en = sc.get("name_en", "")
            diff = sc.get("difficulty_default", "B1")
            st.markdown(f"""
            <div class="scenario-card">
                <div style="font-size:24px;">{icon}</div>
                <div style="font-weight:600;font-size:14px;">{name}</div>
                <div style="font-size:11px;color:#64748b;">{name_en}</div>
                <div style="font-size:11px;color:#8b5cf6;">CEFR {diff}</div>
            </div>
            """, unsafe_allow_html=True)


def render_tool_usage_sidebar(tools_used: List[Dict[str, Any]]) -> None:
    """侧栏工具调用计数。"""
    count: Dict[str, int] = {}
    for t in tools_used:
        name = t.get("name", "unknown")
        count[name] = count.get(name, 0) + 1

    if count:
        st.markdown("#### 📊 Tool Usage")
        for name, cnt in sorted(count.items(), key=lambda x: -x[1]):
            st.markdown(f"- `{name}`: **{cnt}**")
