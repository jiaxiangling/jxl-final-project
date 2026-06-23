# -*- coding: utf-8 -*-
"""自定义 CSS 样式注入。"""


def inject_styles() -> None:
    """注入全局自定义 CSS。"""
    import streamlit as st
    st.markdown("""
    <style>
    /* 特性徽章 */
    .feature-badge {
        display: inline-block; padding: 4px 12px; margin: 2px;
        border-radius: 12px; font-size: 12px; font-weight: 600;
        color: white;
    }
    .badge-agentic { background: #6366f1; }
    .badge-tools { background: #10b981; }
    .badge-multimodal { background: #f59e0b; }
    .badge-prompt { background: #8b5cf6; }

    /* 模式徽章 */
    .mode-badge {
        display: inline-block; padding: 3px 10px; border-radius: 8px;
        font-size: 12px; font-weight: 600;
    }
    .mode-online { background: #dcfce7; color: #166534; }
    .mode-offline { background: #fef3c7; color: #92400e; }

    /* Trace 事件 */
    .trace-event {
        padding: 6px 10px; margin: 3px 0; border-radius: 6px;
        font-size: 13px; border-left: 3px solid;
    }
    .trace-thought { background: #eff6ff; border-color: #3b82f6; }
    .trace-tool { background: #ecfdf5; border-color: #10b981; }
    .trace-result { background: #fffbeb; border-color: #f59e0b; }
    .trace-final { background: #f0fdf4; border-color: #22c55e; }
    .trace-difficulty { background: #faf5ff; border-color: #8b5cf6; }
    .trace-stt { background: #f0f9ff; border-color: #0ea5e9; }
    .trace-tts { background: #f0f9ff; border-color: #0ea5e9; }
    .trace-safety { background: #fef2f2; border-color: #ef4444; }

    /* 决策摘要条 */
    .decision-summary {
        background: #6366f1; color: white; padding: 8px 14px;
        border-radius: 8px; font-size: 13px; font-weight: 500;
        margin: 6px 0;
    }

    /* 工作流图 */
    .workflow-step {
        display: inline-block; padding: 6px 12px; margin: 2px;
        border-radius: 6px; font-size: 12px; font-weight: 500;
        background: #f1f5f9; color: #475569;
    }
    .workflow-step.active { background: #6366f1; color: white; }
    .workflow-arrow { color: #94a3b8; margin: 0 2px; }

    /* 纠错高亮 */
    .correction-block {
        background: #fef2f2; border-left: 3px solid #ef4444;
        padding: 8px 12px; margin: 4px 0; border-radius: 4px; font-size: 14px;
    }
    .hint-block {
        background: #f0fdf4; border-left: 3px solid #22c55e;
        padding: 8px 12px; margin: 4px 0; border-radius: 4px; font-size: 13px;
    }

    /* 难度指示器 */
    .difficulty-indicator {
        display: inline-block; padding: 4px 12px; border-radius: 8px;
        font-size: 13px; font-weight: 600; background: #ede9fe; color: #5b21b6;
    }

    /* 场景卡 */
    .scenario-card {
        padding: 12px; border: 1px solid #e2e8f0; border-radius: 8px;
        cursor: pointer; transition: all 0.2s;
    }
    .scenario-card:hover { border-color: #6366f1; box-shadow: 0 2px 8px rgba(99,102,241,0.15); }
    </style>
    """, unsafe_allow_html=True)
