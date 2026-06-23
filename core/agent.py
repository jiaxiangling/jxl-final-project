# -*- coding: utf-8 -*-
"""课中 ReAct 对话编排器：STT → 思考 → 工具 → 观察 → 回复 → TTS。

这是 agentic workflow 的核心实现，评分命门。
"""

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from config import HISTORY_WINDOW, NO_TOOL_NUDGE_THRESHOLD, get_settings
from core.llm_client import LLMClient, LLMResponse, ToolCall
from core.safety import guard_input, BlockReason
from core.speech import SpeechService
from core.state import LearnerProfile, SessionState, Turn
from core.trace import TraceCollector
from prompts.system_prompt import build_system_prompt
from tools.registry import execute_tool, get_schemas


@dataclass
class TurnResult:
    """单轮对话结果。"""
    reply_text: str = ""
    reply_audio: Optional[bytes] = None
    trace: TraceCollector = field(default_factory=TraceCollector)
    tools_used: List[Dict[str, Any]] = field(default_factory=list)
    mistakes_logged: List[Dict[str, Any]] = field(default_factory=list)
    difficulty_change: Optional[Dict[str, Any]] = None
    user_text: str = ""
    parsed: Dict[str, str] = field(default_factory=dict)   # 解析后的 correction/reply/hint


class ConversationOrchestrator:
    """ReAct 编排器：自主决策何时调工具、纠音、调难度、推进对话。"""

    def __init__(self, llm: LLMClient, speech: SpeechService, profile: LearnerProfile) -> None:
        self.llm = llm
        self.speech = speech
        self.profile = profile
        self._no_tool_streak = 0

    def handle_turn(self, user_input: Union[bytes, str],
                    session: SessionState,
                    scenario: Optional[Dict[str, Any]] = None) -> TurnResult:
        """处理一轮用户输入，返回完整结果。"""
        trace = TraceCollector()
        turn_no = len(session.turns) + 1
        result = TurnResult(trace=trace)

        # ── 1. STT 语音转文字 ──
        if isinstance(user_input, (bytes, bytearray)):
            t0 = time.time()
            trace.add("stt", "Whisper STT", "语音转写中…")
            user_text = self.speech.transcribe(bytes(user_input))
            trace.events[-1].detail = f"转写结果: \"{user_text[:80]}\""
            trace.events[-1].duration_ms = int((time.time() - t0) * 1000)
        else:
            user_text = str(user_input)
        result.user_text = user_text

        # ── 1.5 安全守卫：三层检测（注入→安全→边界）──
        guard = guard_input(user_text)
        trace.add("safety",
                  f"安全检测: {guard.reason.value}",
                  guard.explanation)
        if not guard.allowed:
            # 被拦截：记录轨迹，直接返回安全回复，不调用 LLM
            trace.add("final", f"输入被拦截 ({guard.reason.value})", guard.safe_reply[:200])
            result.reply_text = guard.safe_reply
            result.parsed = {"correction": "", "reply": guard.safe_reply, "hint": ""}

            # TTS 合成安全回复
            if self.speech.available:
                try:
                    audio = self.speech.synthesize(
                        guard.safe_reply, voice=get_settings().tts_voice,
                        speed=get_settings().tts_speed,
                    )
                    result.reply_audio = audio
                except Exception:
                    pass

            turn = Turn(
                turn_no=turn_no,
                user_text=user_text,
                assistant_text=guard.safe_reply,
                assistant_audio=result.reply_audio,
                tool_invocations=[],
                trace=trace.to_list(),
                difficulty_change=None,
            )
            session.append_turn(turn)
            return result

        # ── 2. 组装 messages ──
        system_prompt = build_system_prompt(
            self.profile, scenario, session.difficulty, turn_no,
        )
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
        ]
        messages.extend(session.history_messages(HISTORY_WINDOW))
        messages.append({"role": "user", "content": user_text})

        # 强制兜底提示
        if self._no_tool_streak >= NO_TOOL_NUDGE_THRESHOLD:
            messages.append({"role": "system", "content":
                "Reminder: Please assess the learner's pronunciation or grammar using tools."})

        # ── 3. ReAct 循环 ──
        tools_schema = get_schemas()
        max_iters = get_settings().max_tool_iters
        final_content = ""

        for iteration in range(max_iters):
            t0 = time.time()
            resp = self.llm.chat(messages, tools=tools_schema, temperature=0.4)
            latency = int((time.time() - t0) * 1000)

            # 记录 thought
            if resp.content:
                trace.add("thought", f"思考 (迭代 {iteration + 1})",
                          resp.content[:300], duration_ms=latency)

            # 无工具调用 → 最终回复
            if not resp.tool_calls:
                final_content = resp.content or ""
                trace.add("final", "生成最终回复", final_content[:200])
                self._no_tool_streak += 1
                break

            # 有工具调用 → 逐个执行
            self._no_tool_streak = 0
            # 追加 assistant 消息（含 tool_calls）
            assistant_msg: Dict[str, Any] = {"role": "assistant"}
            if resp.content:
                assistant_msg["content"] = resp.content
            assistant_msg["tool_calls"] = [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.name, "arguments": json.dumps(tc.arguments, ensure_ascii=False)}}
                for tc in resp.tool_calls
            ]
            messages.append(assistant_msg)

            for tc in resp.tool_calls:
                t1 = time.time()
                trace.add("tool_call", tc.name,
                          f"参数: {json.dumps(tc.arguments, ensure_ascii=False)[:200]}")

                # 执行工具
                tool_result = execute_tool(tc.name, tc.arguments, session)
                exec_ms = int((time.time() - t1) * 1000)

                # 记录工具结果
                result_str = json.dumps(tool_result, ensure_ascii=False)[:300]
                trace.add("tool_result", tc.name, result_str, duration_ms=exec_ms)

                # 记录工具使用
                result.tools_used.append({
                    "name": tc.name, "arguments": tc.arguments,
                    "result": tool_result, "iteration": iteration + 1,
                })

                # 处理副作用
                self._apply_side_effects(tc, tool_result, session, trace, result, turn_no)

                # 追加 tool 消息
                messages.append({
                    "role": "tool", "tool_call_id": tc.id,
                    "content": json.dumps(tool_result, ensure_ascii=False),
                })
        else:
            # 达到最大迭代次数，取最后一次 content
            final_content = final_content or "I've completed my analysis. Let me respond now."
            trace.add("final", "达到最大迭代，生成回复", final_content[:200])

        # ── 4. 解析回复 ──
        parsed = parse_reply(final_content)
        result.parsed = parsed
        result.reply_text = final_content

        # ── 5. TTS 语音合成 ──
        if self.speech.available and parsed.get("reply"):
            t0 = time.time()
            settings = get_settings()
            trace.add("tts", "OpenAI TTS", "合成语音中…")
            try:
                audio = self.speech.synthesize(
                    parsed["reply"], voice=settings.tts_voice, speed=settings.tts_speed,
                )
                result.reply_audio = audio
                trace.events[-1].duration_ms = int((time.time() - t0) * 1000)
                trace.events[-1].detail = "语音合成完成"
            except Exception as e:
                trace.events[-1].detail = f"TTS 失败: {e}"
        elif not self.speech.available:
            trace.add("tts", "TTS 不可用", "离线模式，跳过语音合成")

        # ── 6. 构建并保存 Turn ──
        turn = Turn(
            turn_no=turn_no,
            user_text=user_text,
            assistant_text=final_content,
            assistant_audio=result.reply_audio,
            tool_invocations=result.tools_used,
            trace=trace.to_list(),
            difficulty_change=result.difficulty_change,
        )
        session.append_turn(turn)

        return result

    def _apply_side_effects(self, tc: ToolCall, result: Dict[str, Any],
                            session: SessionState, trace: TraceCollector,
                            turn_result: TurnResult, turn_no: int) -> None:
        """处理工具的 session 副作用。"""
        if tc.name == "log_mistake":
            session.add_mistake(
                category=tc.arguments.get("category", "grammar"),
                original=tc.arguments.get("original", ""),
                correction=tc.arguments.get("correction", ""),
                l1_cause=tc.arguments.get("l1_cause", ""),
                turn_no=turn_no,
            )
            turn_result.mistakes_logged.append({
                "category": tc.arguments.get("category", "grammar"),
                "original": tc.arguments.get("original", ""),
                "correction": tc.arguments.get("correction", ""),
            })

        elif tc.name == "adjust_difficulty":
            new_cefr = result.get("new_cefr")
            reason = result.get("reason", "")
            speed = result.get("speed_adjustment")
            topic_depth = result.get("topic_depth")
            if new_cefr and result.get("changed"):
                old = session.difficulty.cefr
                session.difficulty.update(new_cefr, reason, speed, topic_depth)
                turn_result.difficulty_change = {
                    "from": old, "to": new_cefr, "reason": reason,
                }
                trace.add("difficulty", f"难度调整: {old} → {new_cefr}", reason)

        elif tc.name == "lookup_word" or tc.name == "get_phonetics":
            word = tc.arguments.get("word", "")
            if word:
                ipa = result.get("ipa_us") or result.get("ipa", "")
                session.add_vocab(word, ipa, turn_no)


def parse_reply(content: str) -> Dict[str, str]:
    """从 LLM 回复中解析 [CORRECTION]/[REPLY]/[HINT] 标记。"""
    parsed: Dict[str, str] = {"correction": "", "reply": "", "hint": ""}

    # 尝试匹配标记
    corr_match = re.search(r"\[CORRECTION\]\s*(.*?)(?=\[REPLY\]|\[HINT\]|$)", content, re.DOTALL)
    reply_match = re.search(r"\[REPLY\]\s*(.*?)(?=\[CORRECTION\]|\[HINT\]|$)", content, re.DOTALL)
    hint_match = re.search(r"\[HINT\]\s*(.*?)(?=\[CORRECTION\]|\[REPLY\]|$)", content, re.DOTALL)

    if corr_match:
        parsed["correction"] = corr_match.group(1).strip()
    if reply_match:
        parsed["reply"] = reply_match.group(1).strip()
    if hint_match:
        parsed["hint"] = hint_match.group(1).strip()

    # 如果没有标记，整个内容作为 reply
    if not parsed["reply"] and not parsed["correction"]:
        parsed["reply"] = content.strip()

    return parsed
