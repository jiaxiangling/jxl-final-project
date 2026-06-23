# -*- coding: utf-8 -*-
"""课后页：练习反馈 + 数据看板 + 推荐方案。"""

import streamlit as st

from assessment.reporting import generate_session_report, generate_periodic_report
from visualization.charts import (
    error_distribution, learning_hours, progress_trend,
    difficulty_timeline, tool_usage_bar, scenario_coverage,
)
from visualization.export import image_download_button


def render(profile) -> None:
    """渲染课后页。"""
    st.header("📊 Post-Class: Feedback & Dashboard")

    session = st.session_state.get("session")
    if not session or not session.turns:
        st.warning("No practice session found. Please complete a conversation practice first.")
        if st.button("← Go to Practice"):
            st.session_state.stage = "in_class"
            st.rerun()
        return

    # ── 单次反馈 ──
    st.subheader("📋 Session Feedback")
    report = generate_session_report(session)

    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**Summary:** {report.summary}")
        st.markdown(f"**Encouragement:** {report.encouragement}")

        col_s, col_w = st.columns(2)
        with col_s:
            st.markdown("**✅ Strengths:**")
            for s in report.strengths:
                st.markdown(f"- {s}")
        with col_w:
            st.markdown("**⚠️ Areas to Improve:**")
            for w in report.weaknesses:
                st.markdown(f"- {w}")

        if report.key_phrases:
            st.markdown("**🔑 Key Phrases to Review:**")
            for p in report.key_phrases:
                st.markdown(f"- `{p}`")

        if report.new_words:
            st.markdown("**📚 New Vocabulary:**")
            st.markdown(", ".join(f"`{w}`" for w in report.new_words))

    with col2:
        st.metric("CEFR Change", report.cefr_delta)
        st.metric("Total Turns", report.metrics.get("turns", 0))
        st.metric("Error Rate", f"{report.metrics.get('error_rate', 0):.0%}")
        st.metric("Tool Calls", report.metrics.get("tool_calls", 0))

    if report.mistakes_breakdown:
        st.markdown("**Mistake Breakdown:**")
        breakdown_text = " · ".join(f"{k}: {v}" for k, v in report.mistakes_breakdown.items())
        st.markdown(breakdown_text)

    st.divider()

    # ── 数据看板 ──
    st.subheader("📈 Learning Dashboard")

    session_data = session.to_dict()
    all_tools = []
    for t in session.turns:
        all_tools.extend(t.tool_invocations)

    # 第一行图表
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(error_distribution(session.mistakes), use_container_width=True)
    with col2:
        st.plotly_chart(tool_usage_bar(all_tools), use_container_width=True)

    # 第二行图表
    col3, col4 = st.columns(2)
    with col3:
        st.plotly_chart(difficulty_timeline(session_data), use_container_width=True)
    with col4:
        # 学习时长（单会话）
        minutes = session.metrics.get("turns", 0) * 3.0
        st.plotly_chart(learning_hours([{
            "session_id": session.session_id, "turns": session.metrics.get("turns", 0),
        }]), use_container_width=True)

    # 导出
    st.markdown("---")
    col_exp1, col_exp2 = st.columns(2)
    with col_exp1:
        image_download_button(
            error_distribution(session.mistakes),
            filename="error_distribution.png",
            label="📥 Download Error Chart",
        )
    with col_exp2:
        image_download_button(
            difficulty_timeline(session_data),
            filename="difficulty_timeline.png",
            label="📥 Download Difficulty Chart",
        )

    st.divider()

    # ── 周期性评估 ──
    st.subheader("📅 Periodic Assessment")
    periodic = generate_periodic_report(profile.user_id)
    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        st.metric("Total Sessions", periodic.total_sessions)
    with col_p2:
        st.metric("Total Turns", periodic.total_turns)
    with col_p3:
        st.metric("Est. Practice Time", f"{periodic.total_minutes:.0f} min")

    st.markdown(f"**Progress:** {periodic.progress}")
    if periodic.short_boards:
        st.markdown("**Short Boards:**")
        for sb in periodic.short_boards:
            st.markdown(f"- {sb}")
    st.markdown(f"**Trend:** {periodic.trend}")
    st.markdown(f"**Recommendation:** {periodic.recommendation}")

    st.divider()

    # ── 导航 ──
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("← Practice Again", use_container_width=True):
            st.session_state.stage = "in_class"
            st.session_state.reset_session = True
            st.session_state.scenario = None
            st.rerun()
    with col_b:
        if st.button("🏠 Back to Home", use_container_width=True):
            st.session_state.stage = "pre_class"
            st.session_state.pre_step = "info"
            st.rerun()
