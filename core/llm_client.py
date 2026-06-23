# -*- coding: utf-8 -*-
"""LLM 客户端：抽象接口 + OpenAI 实现 + MockLLM 规则大脑（离线降级）。"""

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from config import get_settings, is_online


@dataclass
class ToolCall:
    """一次工具调用。"""
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class LLMResponse:
    """LLM 响应。"""
    content: Optional[str] = None
    tool_calls: List[ToolCall] = field(default_factory=list)
    finish_reason: str = "stop"


class LLMClient(ABC):
    """LLM 客户端抽象接口。"""

    @abstractmethod
    def chat(self, messages: List[Dict[str, Any]],
             tools: Optional[List[Dict[str, Any]]] = None,
             temperature: float = 0.4) -> LLMResponse:
        ...


# ── OpenAI 实现 ───────────────────────────────────────
class OpenAIClient(LLMClient):
    """OpenAI GPT-4o 客户端，支持 function calling。"""

    def __init__(self) -> None:
        from openai import OpenAI
        settings = get_settings()
        self._client = OpenAI(api_key=settings.api_key)
        self._model = settings.llm_model

    def chat(self, messages: List[Dict[str, Any]],
             tools: Optional[List[Dict[str, Any]]] = None,
             temperature: float = 0.4) -> LLMResponse:
        kwargs: Dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = self._client.chat.completions.create(**kwargs)
        msg = response.choices[0].message

        tool_calls: List[ToolCall] = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except json.JSONDecodeError:
                    args = {}
                tool_calls.append(ToolCall(
                    id=tc.id, name=tc.function.name, arguments=args,
                ))

        return LLMResponse(
            content=msg.content,
            tool_calls=tool_calls,
            finish_reason=response.choices[0].finish_reason,
        )


# ── MockLLM 规则大脑（离线降级）────────────────────────
class MockLLMClient(LLMClient):
    """离线规则大脑：模拟 ReAct 行为，产出 thought + tool_calls + 最终回复。

    保证无 API key 时 agentic workflow / function calling / trace 全部可见。
    """

    def __init__(self) -> None:
        self._call_count = 0

    def chat(self, messages: List[Dict[str, Any]],
             tools: Optional[List[Dict[str, Any]]] = None,
             temperature: float = 0.4) -> LLMResponse:
        self._call_count += 1

        # 找到最后一条 user 消息
        user_text = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_text = m.get("content", "")
                break

        # 检查是否已有 tool 结果消息（如果有 → 生成最终回复）
        has_tool_result = any(m.get("role") == "tool" for m in messages)

        if has_tool_result:
            return self._generate_final_reply(messages, user_text)
        else:
            return self._generate_tool_calls(user_text, messages)

    def _generate_tool_calls(self, user_text: str, messages: List[Dict[str, Any]]) -> LLMResponse:
        """分析用户输入，决定调用哪些工具。"""
        text_lower = user_text.lower()
        tool_calls: List[ToolCall] = []
        thought_parts: List[str] = []

        # 1. 检测生词询问
        word_match = re.search(r"(?:what does|what is|what's|meaning of)\s+['\"]?(\w+)['\"]?", text_lower)
        if word_match:
            word = word_match.group(1)
            thought_parts.append(f"The user asked about '{word}' — I'll look it up.")
            tool_calls.append(ToolCall(
                id=f"call_{len(tool_calls)}", name="lookup_word",
                arguments={"word": word, "context": user_text},
            ))
            tool_calls.append(ToolCall(
                id=f"call_{len(tool_calls)}", name="get_phonetics",
                arguments={"word": word},
            ))

        # 2. 总是评估发音（模拟每2-3轮纠音）
        # 从 system prompt 或 messages 中推断 l1（简化：默认 zh）
        l1 = "zh"
        for m in messages:
            if m.get("role") == "system" and "Spanish" in m.get("content", ""):
                l1 = "es"
                break

        thought_parts.append("I'll check for L1 transfer errors in the learner's utterance.")
        tool_calls.append(ToolCall(
            id=f"call_{len(tool_calls)}", name="assess_pronunciation",
            arguments={"transcript": user_text, "learner_l1": l1},
        ))

        # 3. 检测常见错误模式 → log_mistake
        mistake = self._detect_mistake(text_lower, l1)
        if mistake:
            thought_parts.append(f"Detected a {mistake['category']} error — logging it.")
            tool_calls.append(ToolCall(
                id=f"call_{len(tool_calls)}", name="log_mistake",
                arguments=mistake,
            ))

        # 4. 每3轮调一次难度
        user_msg_count = sum(1 for m in messages if m.get("role") == "user")
        if user_msg_count > 0 and user_msg_count % 3 == 0:
            thought_parts.append("Time to check if difficulty needs adjustment.")
            tool_calls.append(ToolCall(
                id=f"call_{len(tool_calls)}", name="adjust_difficulty",
                arguments={"current_level": "B1", "recent_metrics": {"fluency": 3.5, "error_rate": 0.3, "turns": user_msg_count}},
            ))

        # 5. 第一轮且是新场景 → 取课程
        if user_msg_count <= 1:
            # 尝试从 system prompt 提取 scenario_id
            scenario_id = "housing"
            for m in messages:
                content = m.get("content", "")
                match = re.search(r"Scenario:\s*\w+\s*\((\w+)\)", content)
                if match:
                    scenario_id = match.group(1)
                    break
            thought_parts.append(f"Let me retrieve the curriculum for this scenario.")
            tool_calls.append(ToolCall(
                id=f"call_{len(tool_calls)}", name="get_scenario_curriculum",
                arguments={"scenario_id": scenario_id, "cefr_level": "B1"},
            ))

        thought = "💭 " + " ".join(thought_parts) if thought_parts else "💭 Let me respond to the learner."
        return LLMResponse(content=thought, tool_calls=tool_calls, finish_reason="tool_calls")

    def _detect_mistake(self, text: str, l1: str) -> Optional[Dict[str, Any]]:
        """检测常见 L1 错误，返回 log_mistake 参数。"""
        # 中文 L1 常见错误
        zh_patterns = [
            (r"\bi no like\b", "grammar", "I no like", "I don't like", "Missing auxiliary 'don't'"),
            (r"\bi want rent\b", "grammar", "I want rent", "I'd like to rent", "Missing article and 'to'"),
            (r"\bopen the light\b", "translation", "open the light", "turn on the light", "Chinglish: open→turn on"),
            (r"\bis available\??$", "grammar", "Is available?", "Is it available?", "Missing subject (pro-drop)"),
            (r"\byesterday i go\b", "grammar", "Yesterday I go", "Yesterday I went", "Past tense needed"),
            (r"\btwo book\b", "grammar", "two book", "two books", "Missing plural -s"),
            (r"\bhe go\b", "grammar", "he go", "he goes", "Subject-verb agreement"),
            (r"\bdepend of\b", "grammar", "depend of", "depend on", "Wrong preposition"),
            (r"\bmore better\b", "grammar", "more better", "better", "Redundant comparative"),
        ]
        for pattern, cat, orig, corr, cause in zh_patterns:
            if re.search(pattern, text):
                return {"category": cat, "original": orig, "correction": corr, "l1_cause": cause}
        return None

    def _generate_final_reply(self, messages: List[Dict[str, Any]], user_text: str) -> LLMResponse:
        """工具执行完毕后，生成最终教练回复。"""
        text_lower = user_text.lower()

        # 检查是否有纠错
        correction_block = ""
        mistake = self._detect_mistake(text_lower, "zh")
        if mistake:
            correction_block = (
                f"[CORRECTION]\n"
                f'"{mistake["original"]}" → "{mistake["correction"]}"\n'
                f'Reason: {mistake["l1_cause"]}\n'
            )

        # 生成场景化回复
        reply = self._scenario_reply(user_text, messages)

        # 生成提示
        hint = "[HINT]\nKeep practicing! Try saying the corrected sentence out loud.\n"

        full_reply = correction_block + "[REPLY]\n" + reply + "\n" + hint
        return LLMResponse(content=full_reply, tool_calls=[], finish_reason="stop")

    def _scenario_reply(self, user_text: str, messages: List[Dict[str, Any]]) -> str:
        """生成场景化回复（模板化）。"""
        text_lower = user_text.lower()

        # 检测场景
        scenario = "general"
        for m in messages:
            content = m.get("content", "")
            for s in ["housing", "medical", "interview", "campus", "transit", "bank", "restaurant", "workplace"]:
                if s in content.lower():
                    scenario = s
                    break

        # 通用鼓励 + 场景化推进
        if "hello" in text_lower or "hi" in text_lower:
            return ("Hi there! I'm SpeakEasy, your English speaking coach. "
                    "I'm here to help you practice real-life conversations. "
                    "What would you like to talk about today?")

        if scenario == "housing":
            return ("That's great! When looking for an apartment, it's helpful to ask about "
                    "the lease terms, security deposit, and whether utilities are included. "
                    "Could you tell me what area you're hoping to rent in?")
        if scenario == "interview":
            return ("Excellent! For interviews, using the STAR method helps structure your answers. "
                    "Could you tell me about a challenge you faced at work and how you handled it?")
        if scenario == "medical":
            return ("I understand. When visiting a doctor, it's important to describe your symptoms clearly. "
                    "Could you tell me what symptoms you've been experiencing?")
        if scenario == "restaurant":
            return ("Perfect! When ordering at a restaurant, you can say 'I'd like to order...' "
                    "What would you like to order today?")

        return ("That's a good attempt! Let's keep the conversation going. "
                "Could you tell me more about what you're trying to say?")


def get_llm() -> LLMClient:
    """根据模式返回 LLM 客户端实例。"""
    if is_online():
        try:
            return OpenAIClient()
        except Exception:
            return MockLLMClient()
    return MockLLMClient()
