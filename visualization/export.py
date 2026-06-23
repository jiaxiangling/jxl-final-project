# -*- coding: utf-8 -*-
"""图片导出：kaleido 优先，matplotlib 回退。"""

import io
from typing import Optional

import plotly.graph_objects as go


def to_image_bytes(fig: go.Figure, fmt: str = "png", width: int = 800, height: int = 500) -> Optional[bytes]:
    """将 Plotly 图表导出为图片 bytes。

    优先使用 kaleido，失败则回退 matplotlib 静态渲染。
    """
    # 尝试 kaleido
    try:
        img_bytes = fig.to_image(format=fmt, width=width, height=height, scale=2)
        return img_bytes
    except Exception:
        pass

    # 回退：用 matplotlib 简单渲染
    try:
        return _matplotlib_fallback(fig, fmt, width, height)
    except Exception:
        return None


def _matplotlib_fallback(fig: go.Figure, fmt: str, width: int, height: int) -> Optional[bytes]:
    """matplotlib 回退渲染。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig_mat, ax = plt.subplots(figsize=(width / 100, height / 100))

    # 提取标题
    title = ""
    if fig.layout.title and fig.layout.title.text:
        title = fig.layout.title.text
    ax.set_title(title)

    # 提取数据（简化：只处理 Bar 和 Pie）
    for trace in fig.data:
        if hasattr(trace, "x") and hasattr(trace, "y") and trace.x is not None and trace.y is not None:
            ax.bar(list(trace.x), list(trace.y), color="#6366f1", alpha=0.7)
            ax.set_xlabel(fig.layout.xaxis.title.text if fig.layout.xaxis.title else "")
            ax.set_ylabel(fig.layout.yaxis.title.text if fig.layout.yaxis.title else "")
        elif hasattr(trace, "labels") and hasattr(trace, "values"):
            ax.pie(list(trace.values), labels=list(trace.labels), autopct="%1.0f%%",
                   colors=["#ef4444", "#f59e0b", "#6366f1", "#10b981", "#22c55e"])

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    buf = io.BytesIO()
    fig_mat.savefig(buf, format=fmt, dpi=150, bbox_inches="tight")
    plt.close(fig_mat)
    buf.seek(0)
    return buf.getvalue()


def image_download_button(fig: go.Figure, filename: str = "chart.png",
                          label: str = "📥 Download as PNG") -> None:
    """在 Streamlit 中渲染图片下载按钮。"""
    import streamlit as st

    img_bytes = to_image_bytes(fig, "png")
    if img_bytes:
        st.download_button(
            label=label,
            data=img_bytes,
            file_name=filename,
            mime="image/png",
        )
    else:
        st.warning("图片导出不可用（kaleido 未安装）。请在浏览器中右键图表保存。")
