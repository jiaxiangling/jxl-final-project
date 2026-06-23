# -*- coding: utf-8 -*-
"""数据模型与会话状态管理。"""

import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from config import SESSIONS_DIR, ensure_dirs


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _uid(prefix: str = "u") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


# ── 学习者画像 ────────────────────────────────────────
@dataclass
class LearnerProfile:
    user_id: str = field(default_factory=lambda: _uid("u"))
    name: str = ""
    l1: str = "zh"                       # "zh" | "es"
    age: int = 25
    occupation: str = ""
    baseline_level: str = "B1"          # 自评 CEFR
    goals: List[str] = field(default_factory=list)          # workplace / interview / daily_life / exam
    pain_scenarios: List[str] = field(default_factory=list) # scenario ids
    placement_scores: Dict[str, int] = field(default_factory=dict)  # listening/speaking/reading/writing
    cefr: str = "B1"                     # 当前 CEFR（动态）
    learning_path: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "LearnerProfile":
        return cls(**{k: d.get(k) for k in cls.__dataclass_fields__})


# ── 难度状态 ──────────────────────────────────────────
@dataclass
class DifficultyState:
    cefr: str = "B1"
    speed: float = 1.0
    topic_depth: str = "moderate"       # shallow / moderate / deep
    history: List[Dict[str, Any]] = field(default_factory=list)

    def update(self, new_cefr: str, reason: str, speed: Optional[float] = None,
               topic_depth: Optional[str] = None) -> None:
        entry = {"from": self.cefr, "to": new_cefr, "reason": reason,
                 "speed": speed, "topic_depth": topic_depth, "ts": _now()}
        self.history.append(entry)
        self.cefr = new_cefr
        if speed is not None:
            self.speed = speed
        if topic_depth is not None:
            self.topic_depth = topic_depth


# ── 单轮对话记录 ──────────────────────────────────────
@dataclass
class Turn:
    turn_no: int
    user_text: str = ""
    assistant_text: str = ""
    assistant_audio: Optional[bytes] = None   # 不持久化
    tool_invocations: List[Dict[str, Any]] = field(default_factory=list)
    trace: List[Dict[str, Any]] = field(default_factory=list)
    difficulty_change: Optional[Dict[str, Any]] = None
    ts: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d.pop("assistant_audio", None)        # bytes 不可 JSON 序列化
        return d


# ── 会话状态 ──────────────────────────────────────────
@dataclass
class SessionState:
    session_id: str = field(default_factory=lambda: _uid("s"))
    user_id: str = ""
    scenario_id: str = ""
    started_at: str = field(default_factory=_now)
    ended_at: Optional[str] = None
    turns: List[Turn] = field(default_factory=list)
    mistakes: List[Dict[str, Any]] = field(default_factory=list)
    difficulty: DifficultyState = field(default_factory=DifficultyState)
    vocab: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=lambda: {
        "turns": 0, "error_rate": 0.0, "fluency": 0.0,
        "total_audio_sec": 0, "tool_calls": 0,
    })
    voice_enabled: bool = True

    # ── 对话历史（供 LLM） ──
    def history_messages(self, window: int = 12) -> List[Dict[str, str]]:
        msgs: List[Dict[str, str]] = []
        recent = self.turns[-window:]
        for t in recent:
            if t.user_text:
                msgs.append({"role": "user", "content": t.user_text})
            if t.assistant_text:
                msgs.append({"role": "assistant", "content": t.assistant_text})
        return msgs

    def append_turn(self, turn: Turn) -> None:
        self.turns.append(turn)
        self.metrics["turns"] = len(self.turns)
        self.metrics["tool_calls"] = sum(
            len(t.tool_invocations) for t in self.turns
        )
        if self.mistakes:
            err_count = len(self.mistakes)
            self.metrics["error_rate"] = round(err_count / max(self.metrics["turns"], 1), 2)

    def add_mistake(self, category: str, original: str, correction: str,
                    l1_cause: str = "", turn_no: int = 0) -> int:
        self.mistakes.append({
            "category": category, "original": original, "correction": correction,
            "l1_cause": l1_cause, "turn": turn_no, "ts": _now(),
        })
        return len(self.mistakes)

    def add_vocab(self, word: str, ipa: str = "", turn_no: int = 0) -> None:
        if not any(v.get("word") == word for v in self.vocab):
            self.vocab.append({"word": word, "ipa": ipa, "added_turn": turn_no,
                               "mastered": False, "ts": _now()})

    # ── 持久化 ──
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id, "user_id": self.user_id,
            "scenario_id": self.scenario_id, "started_at": self.started_at,
            "ended_at": self.ended_at,
            "turns": [t.to_dict() for t in self.turns],
            "mistakes": self.mistakes,
            "difficulty": asdict(self.difficulty),
            "vocab": self.vocab,
            "metrics": self.metrics,
            "voice_enabled": self.voice_enabled,
        }

    def save(self) -> None:
        ensure_dirs()
        user_dir = os.path.join(SESSIONS_DIR, self.user_id)
        os.makedirs(user_dir, exist_ok=True)
        path = os.path.join(user_dir, f"{self.session_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SessionState":
        diff_d = d.get("difficulty", {})
        difficulty = DifficultyState(
            cefr=diff_d.get("cefr", "B1"),
            speed=diff_d.get("speed", 1.0),
            topic_depth=diff_d.get("topic_depth", "moderate"),
            history=diff_d.get("history", []),
        )
        turns = [Turn(**t) for t in d.get("turns", [])]
        return cls(
            session_id=d.get("session_id", _uid("s")),
            user_id=d.get("user_id", ""),
            scenario_id=d.get("scenario_id", ""),
            started_at=d.get("started_at", _now()),
            ended_at=d.get("ended_at"),
            turns=turns,
            mistakes=d.get("mistakes", []),
            difficulty=difficulty,
            vocab=d.get("vocab", []),
            metrics=d.get("metrics", {}),
            voice_enabled=d.get("voice_enabled", True),
        )


def load_user_sessions(user_id: str) -> List[Dict[str, Any]]:
    """加载某用户的所有历史会话摘要。"""
    ensure_dirs()
    user_dir = os.path.join(SESSIONS_DIR, user_id)
    if not os.path.isdir(user_dir):
        return []
    sessions: List[Dict[str, Any]] = []
    for fname in sorted(os.listdir(user_dir), reverse=True):
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(user_dir, fname), encoding="utf-8") as f:
                data = json.load(f)
            sessions.append({
                "session_id": data["session_id"],
                "scenario_id": data.get("scenario_id", ""),
                "started_at": data.get("started_at", ""),
                "turns": len(data.get("turns", [])),
                "metrics": data.get("metrics", {}),
            })
        except (json.JSONDecodeError, KeyError):
            continue
    return sessions


def load_session(user_id: str, session_id: str) -> Optional[SessionState]:
    path = os.path.join(SESSIONS_DIR, user_id, f"{session_id}.json")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        return SessionState.from_dict(json.load(f))
