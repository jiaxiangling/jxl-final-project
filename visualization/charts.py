# -*- coding: utf-8 -*-
"""Plotly 可视化图表：雷达图 / 仪表盘 / 趋势 / 分布 / 热力图 / 时间线。"""

from typing import Any, Dict, List, Optional

import plotly.graph_objects as go

# 配色
COLORS = {
    "primary": "#6366f1",
    "zh": "#3b82f6",
    "es": "#10b981",
    "warning": "#f59e0b",
    "danger": "#ef4444",
    "success": "#22c55e",
    "bg": "rgba(0,0,0,0)",
}


def radar_chart(scores: Dict[str, int], cefr: str = "B1", l1: str = "zh") -> go.Figure:
    """四维度掌握度雷达图（听说读写）。"""
    dims = ["Listening", "Speaking", "Reading", "Writing"]
    keys = ["listening", "speaking", "reading", "writing"]
    values = [scores.get(k, 50) for k in keys]

    color = COLORS["zh"] if l1 == "zh" else COLORS["es"]

    fig = go.Figure(data=go.Scatterpolar(
        r=values + [values[0]],
        theta=dims + [dims[0]],
        fill="toself",
        fillcolor=color,
        line=dict(color=color, width=2),
        opacity=0.6,
        name=f"CEFR {cefr}",
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(size=10)),
        ),
        title=dict(text=f"English Proficiency — CEFR {cefr}", x=0.5),
        showlegend=True,
        height=400,
        paper_bgcolor=COLORS["bg"],
        plot_bgcolor=COLORS["bg"],
    )
    return fig


def cefr_gauge(cefr: str) -> go.Figure:
    """CEFR 级别仪表盘。"""
    from config import CEFR_NUMERIC
    value = CEFR_NUMERIC.get(cefr, 3)
    steps = []
    colors = ["#93c5fd", "#60a5fa", "#3b82f6", "#6366f1", "#8b5cf6", "#a855f7"]
    for i, lvl in enumerate(["A1", "A2", "B1", "B2", "C1", "C2"]):
        steps.append(dict(range=[i + 0.5, i + 1.5], color=colors[i], label=lvl))

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title=dict(text=f"CEFR Level: {cefr}"),
        gauge=dict(
            axis=dict(range=[0.5, 6.5], tickwidth=1, tickvals=list(range(1, 7)),
                      ticktext=["A1", "A2", "B1", "B2", "C1", "C2"]),
            bar=dict(color=COLORS["primary"]),
            steps=[dict(range=[s["range"][0], s["range"][1]], color=s["color"]) for s in steps],
        ),
    ))
    fig.update_layout(height=300, paper_bgcolor=COLORS["bg"])
    return fig


def error_distribution(mistakes: List[Dict[str, Any]]) -> go.Figure:
    """错误类型分布饼图。"""
    category_count: Dict[str, int] = {}
    for m in mistakes:
        cat = m.get("category", "grammar")
        category_count[cat] = category_count.get(cat, 0) + 1

    if not category_count:
        category_count = {"No errors": 1}

    labels = list(category_count.keys())
    values = list(category_count.values())
    colors = [COLORS["danger"], COLORS["warning"], COLORS["primary"], COLORS["es"], COLORS["success"]]

    fig = go.Figure(data=go.Pie(
        labels=labels, values=values,
        hole=0.4,
        marker=dict(colors=colors[:len(labels)]),
        textinfo="label+percent",
    ))
    fig.update_layout(
        title=dict(text="Mistake Type Distribution", x=0.5),
        height=350, paper_bgcolor=COLORS["bg"],
    )
    return fig


def learning_hours(sessions: List[Dict[str, Any]]) -> go.Figure:
    """学习时长趋势（按会话）。"""
    if not sessions:
        sessions = [{"session_id": "s1", "turns": 0, "started_at": "N/A"}]

    labels = [f"S{i+1}" for i in range(len(sessions))]
    minutes = [s.get("turns", 0) * 3.0 for s in sessions]

    fig = go.Figure(data=go.Bar(
        x=labels, y=minutes,
        marker_color=COLORS["primary"],
        text=[f"{m:.0f}m" for m in minutes],
        textposition="outside",
    ))
    fig.update_layout(
        title=dict(text="Practice Time per Session", x=0.5),
        xaxis_title="Session", yaxis_title="Minutes",
        height=300, paper_bgcolor=COLORS["bg"], plot_bgcolor=COLORS["bg"],
    )
    return fig


def progress_trend(sessions: List[Dict[str, Any]]) -> go.Figure:
    """CEFR 进步趋势 + 错误率趋势。"""
    if not sessions:
        sessions = [{"metrics": {"error_rate": 0.3, "turns": 5}}]

    from config import CEFR_NUMERIC
    labels = [f"S{i+1}" for i in range(len(sessions))]
    error_rates = [s.get("metrics", {}).get("error_rate", 0) * 100 for s in sessions]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=labels, y=error_rates, mode="lines+markers",
        name="Error Rate (%)", line=dict(color=COLORS["danger"], width=2),
        yaxis="y",
    ))
    fig.update_layout(
        title=dict(text="Progress Trend", x=0.5),
        xaxis_title="Session",
        yaxis=dict(title="Error Rate (%)", side="left"),
        height=300, paper_bgcolor=COLORS["bg"], plot_bgcolor=COLORS["bg"],
        showlegend=True,
    )
    return fig


def difficulty_timeline(session: Dict[str, Any]) -> go.Figure:
    """单会话内难度自适应时间线。"""
    history = session.get("difficulty", {}).get("history", [])
    if not history:
        # 模拟数据
        history = [{"from": "B1", "to": "B1", "reason": "Starting level", "ts": "start"}]

    from config import CEFR_NUMERIC
    labels = [f"Turn {i+1}" for i in range(len(history))]
    levels = [CEFR_NUMERIC.get(h.get("to", "B1"), 3) for h in history]
    level_labels = [h.get("to", "B1") for h in history]

    fig = go.Figure(data=go.Scatter(
        x=labels, y=levels, mode="lines+markers+text",
        text=level_labels, textposition="top center",
        line=dict(color=COLORS["primary"], width=2, shape="hv"),
        marker=dict(size=10),
    ))
    fig.update_layout(
        title=dict(text="Difficulty Adaptation Timeline", x=0.5),
        xaxis_title="Adjustment Point",
        yaxis=dict(title="CEFR Level", tickvals=list(range(1, 7)),
                   ticktext=["A1", "A2", "B1", "B2", "C1", "C2"]),
        height=300, paper_bgcolor=COLORS["bg"], plot_bgcolor=COLORS["bg"],
    )
    return fig


def tool_usage_bar(tools_used: List[Dict[str, Any]]) -> go.Figure:
    """工具调用次数分布。"""
    count: Dict[str, int] = {}
    for t in tools_used:
        name = t.get("name", "unknown")
        count[name] = count.get(name, 0) + 1

    if not count:
        count = {"No tools used": 1}

    names = list(count.keys())
    values = list(count.values())

    fig = go.Figure(data=go.Bar(
        x=names, y=values,
        marker_color=COLORS["es"],
        text=values, textposition="outside",
    ))
    fig.update_layout(
        title=dict(text="Tool Usage (Function Calling)", x=0.5),
        xaxis_title="Tool", yaxis_title="Calls",
        height=300, paper_bgcolor=COLORS["bg"], plot_bgcolor=COLORS["bg"],
    )
    return fig


def scenario_coverage(sessions: List[Dict[str, Any]]) -> go.Figure:
    """场景覆盖分布。"""
    count: Dict[str, int] = {}
    for s in sessions:
        sc = s.get("scenario_id", "free") or "free"
        count[sc] = count.get(sc, 0) + 1

    if not count:
        count = {"housing": 1}

    fig = go.Figure(data=go.Bar(
        x=list(count.keys()), y=list(count.values()),
        marker_color=COLORS["warning"],
        text=list(count.values()), textposition="outside",
    ))
    fig.update_layout(
        title=dict(text="Scenario Coverage", x=0.5),
        xaxis_title="Scenario", yaxis_title="Sessions",
        height=300, paper_bgcolor=COLORS["bg"], plot_bgcolor=COLORS["bg"],
    )
    return fig
