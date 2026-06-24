# -*- coding: utf-8 -*-
"""可复用 UI 组件：徽章 / trace 面板 / 聊天气泡 / 工具卡 / 工作流图 / 提示词查看器。"""

import base64
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

    # 把所有 trace 事件拼成一个 HTML 块，一次性渲染，避免多个 st.markdown 触发 DOM 冲突
    summary = trace.decision_summary()
    parts = [f'<div class="decision-summary">{summary}</div>']

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

        parts.append(
            f'<div class="trace-event {css_class}">'
            f'{icon} <strong>Step {event.step}: {html.escape(event.title)}</strong>{ms_html}'
            f'{detail_html}</div>'
        )

    st.markdown("".join(parts), unsafe_allow_html=True)


def render_chat_message(role: str, text: str, audio: Optional[bytes] = None,
                        parsed: Optional[Dict[str, str]] = None) -> None:
    """渲染聊天气泡（含纠错高亮和音频播放）。"""
    with st.chat_message(role):
        if parsed:
            # 把所有自定义 HTML 块合并为一次渲染，避免 DOM 冲突
            html_parts = []
            if parsed.get("correction"):
                html_parts.append(f'<div class="correction-block">📝 <strong>Correction:</strong><br>{html.escape(parsed["correction"])}</div>')
            if parsed.get("hint"):
                html_parts.append(f'<div class="hint-block">💡 {html.escape(parsed["hint"])}</div>')
            if html_parts:
                st.markdown("".join(html_parts), unsafe_allow_html=True)
            if parsed.get("reply"):
                st.markdown(parsed["reply"])
        else:
            st.markdown(text)

        # 音频播放（使用原生 HTML audio 标签规避 st.audio DOM 冲突）
        if audio:
            b64 = base64.b64encode(audio).decode("utf-8")
            st.markdown(
                f'<audio controls style="width:100%" '
                f'src="data:audio/mp3;base64,{b64}"></audio>',
                unsafe_allow_html=True,
            )


def system_prompt_viewer(prompt: str, key_suffix: str = "default") -> None:
    """系统提示词查看器（按 === 分节折叠）。"""
    sections = prompt.split("=== ")
    with st.expander("📝 View System Prompt Architecture", expanded=False):
        st.caption("This is the complete system prompt that defines the AI coach's role, boundaries, rules, and safety constraints.")
        # 使用 selectbox 切换章节，避免 expander 嵌套
        titles = []
        bodies = {}
        for section in sections:
            if not section.strip():
                continue
            parts = section.split(" ===", 1)
            title = parts[0].strip()
            body = parts[1].strip() if len(parts) > 1 else ""
            if title:
                titles.append(title)
                bodies[title] = body[:2000] + ("..." if len(body) > 2000 else "")

        if titles:
            selected = st.selectbox("Section", titles, key=f"sys_prompt_section_{key_suffix}")
            st.text(bodies.get(selected, ""))


def tool_summary_card(tools_used: List[Dict[str, Any]]) -> None:
    """本轮工具调用汇总卡。"""
    if not tools_used:
        return
    st.markdown("#### 🔧 Tool Calls This Turn")
    for idx, t in enumerate(tools_used):
        name = t.get("name", "?")
        args = t.get("arguments", {})
        result = t.get("result", {})
        with st.expander(f"🔧 {name}", expanded=False):
            st.json({"arguments": args, "result": result})


def scenario_grid(scenarios: List[Dict[str, Any]]) -> None:
    """场景卡片网格。"""
    cols = st.columns(4)
    # 把所有场景卡 HTML 按列收集后一次渲染，避免循环多次 unsafe_allow_html 产生 DOM 冲突
    col_htmls: Dict[int, List[str]] = {c: [] for c in range(4)}
    for i, sc in enumerate(scenarios):
        col_idx = i % 4
        icon = sc.get("icon", "💬")
        name = sc.get("name_zh", sc.get("id", ""))
        name_en = sc.get("name_en", "")
        diff = sc.get("difficulty_default", "B1")
        col_htmls[col_idx].append(
            f'<div class="scenario-card">'
            f'<div style="font-size:24px;">{icon}</div>'
            f'<div style="font-weight:600;font-size:14px;">{html.escape(name)}</div>'
            f'<div style="font-size:11px;color:#64748b;">{html.escape(name_en)}</div>'
            f'<div style="font-size:11px;color:#8b5cf6;">CEFR {html.escape(diff)}</div>'
            f'</div>'
        )
    for col_idx, col in enumerate(cols):
        with col:
            if col_htmls[col_idx]:
                st.markdown("".join(col_htmls[col_idx]), unsafe_allow_html=True)


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
