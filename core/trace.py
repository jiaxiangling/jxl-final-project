# -*- coding: utf-8 -*-
"""Agent 决策轨迹收集器：记录 ReAct 循环的每一步。"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class TraceEvent:
    """单条轨迹事件。"""
    step: int
    kind: str            # thought / tool_call / tool_result / final / stt / tts / difficulty / state_update
    title: str
    detail: str = ""
    ts: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    duration_ms: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step, "kind": self.kind, "title": self.title,
            "detail": self.detail, "ts": self.ts,
            "duration_ms": self.duration_ms, "extra": self.extra,
        }


class TraceCollector:
    """收集一轮对话中的所有轨迹事件。"""

    # 事件图标（供 UI 渲染）
    ICONS = {
        "thought": "💭", "tool_call": "🔧", "tool_result": "📋",
        "final": "✅", "stt": "🎙️", "tts": "🔊",
        "difficulty": "📊", "state_update": "💾", "safety": "🛡️",
    }

    def __init__(self) -> None:
        self._events: List[TraceEvent] = []
        self._step: int = 0

    def add(self, kind: str, title: str, detail: str = "",
            duration_ms: int = 0, extra: Optional[Dict[str, Any]] = None) -> TraceEvent:
        self._step += 1
        event = TraceEvent(
            step=self._step, kind=kind, title=title, detail=detail,
            duration_ms=duration_ms, extra=extra or {},
        )
        self._events.append(event)
        return event

    @property
    def events(self) -> List[TraceEvent]:
        return list(self._events)

    def reset(self) -> None:
        self._events.clear()
        self._step = 0

    def to_list(self) -> List[Dict[str, Any]]:
        return [e.to_dict() for e in self._events]

    def decision_summary(self) -> str:
        """生成本轮决策摘要条（供 UI 高亮显示）。"""
        actions: List[str] = []
        for e in self._events:
            if e.kind == "tool_call":
                name = e.title
                # 简化工具名
                short = {
                    "assess_pronunciation": "纠音",
                    "lookup_word": "查词",
                    "get_phonetics": "音标",
                    "suggest_sentence_patterns": "句型替换",
                    "expand_examples": "例句",
                    "adjust_difficulty": "调难度",
                    "log_mistake": "记错",
                    "generate_session_feedback": "生成反馈",
                    "get_scenario_curriculum": "取课程",
                    "plan_learning_path": "规划路径",
                }.get(name, name)
                actions.append(short)
            elif e.kind == "difficulty":
                actions.append(e.title)
            elif e.kind == "safety":
                actions.append("🛡️安全拦截")

        if not actions:
            return "本轮：直接回复（无需工具）"

        return "本轮自主决策：" + " + ".join(actions)

    def tool_call_count(self) -> int:
        return sum(1 for e in self._events if e.kind == "tool_call")
