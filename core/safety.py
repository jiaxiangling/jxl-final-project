# -*- coding: utf-8 -*-
"""安全守卫：提示注入防护 + 对话边界约束 + 内容安全过滤。

三层防护：
  1. 提示注入检测  — 拦截越狱/角色篡改/系统提示窃取指令
  2. 内容安全过滤  — 屏蔽暴力、低俗、敏感内容
  3. 对话边界约束  — 引导离题内容回到英语学习场景
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class BlockReason(Enum):
    PROMPT_INJECTION   = "prompt_injection"
    CONTENT_SAFETY     = "content_safety"
    OFF_TOPIC          = "off_topic"
    CLEAN              = "clean"


@dataclass
class GuardResult:
    allowed: bool
    reason: BlockReason
    explanation: str        # 给 UI trace 展示的原因
    safe_reply: str         # 被拦截时返回给用户的安全回复


# ── 1. 提示注入模式 ────────────────────────────────────
# 检测越狱/角色篡改/系统提示窃取指令
_INJECTION_PATTERNS: List[re.Pattern] = [
    # 忽略/覆盖系统指令
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above|your)\s+(instructions?|prompts?|rules?|system)", re.I),
    re.compile(r"(forget|disregard|override|bypass)\s+(your\s+)?(instructions?|rules?|training|guidelines?)", re.I),
    re.compile(r"you\s+are\s+now\s+(a\s+)?(different|new|another|evil|jailbroken|unrestricted|free)", re.I),
    re.compile(r"(act|pretend|roleplay|imagine)\s+(as\s+)?(if\s+)?(you\s+(are|were|have no|don't have)|a\s+)", re.I),
    # 窃取系统提示
    re.compile(r"(print|show|reveal|repeat|output|tell me|give me|what\s+is|display)\s+(your\s+)?(system\s+prompt|initial\s+prompt|original\s+instructions?|hidden\s+instructions?|secret\s+prompt)", re.I),
    re.compile(r"(what\s+(are|were)\s+your\s+(instructions?|rules?|system\s+prompt))", re.I),
    # DAN / 越狱关键词
    re.compile(r"\b(DAN|jailbreak|do anything now|no\s+restrictions?|unrestricted\s+mode|developer\s+mode)\b", re.I),
    # 角色扮演绕过
    re.compile(r"pretend\s+(you\s+)?(are\s+)?(not\s+an?\s+ai|human|without\s+rules?)", re.I),
    re.compile(r"hypothetically\s+(speaking\s+)?(if\s+you\s+had\s+no\s+limits|with\s+no\s+restrictions)", re.I),
    # 中文注入模式
    re.compile(r"(忽略|忘记|跳过|覆盖).{0,10}(之前|上面|所有|全部).{0,10}(指令|规则|限制|提示词|系统提示)", re.I),
    re.compile(r"(你现在是|你是一个|扮演).{0,20}(没有限制|不受约束|自由|邪恶|另一个)", re.I),
    re.compile(r"(告诉我|输出|显示|打印).{0,10}(你的系统提示|你的指令|你的规则)", re.I),
]

# ── 2. 内容安全模式 ────────────────────────────────────
_CONTENT_SAFETY_PATTERNS: List[re.Pattern] = [
    # 暴力/伤害
    re.compile(r"\b(how\s+to\s+(kill|murder|hurt|harm|attack|bomb|shoot)\s+(someone|people|a\s+person))\b", re.I),
    re.compile(r"\b(suicide|self.?harm|cut\s+myself|kill\s+myself|end\s+my\s+life)\b", re.I),
    # 非法内容
    re.compile(r"\b(how\s+to\s+(make|build|create)\s+(a\s+)?(bomb|weapon|explosive|drug))\b", re.I),
    re.compile(r"\b(buy|sell|obtain)\s+(illegal\s+)?(drugs?|weapons?|firearms?)\b", re.I),
    # 低俗内容（仅强烈词汇，避免过度过滤）
    re.compile(r"\b(pornograph|explicit\s+sexual|nude\s+image|sex\s+video)\b", re.I),
    # 中文危险词
    re.compile(r"(如何|怎么|怎样).{0,8}(制作|制造|合成).{0,8}(炸弹|毒品|武器)", re.I),
    re.compile(r"(自杀|自伤|伤害自己|结束生命)", re.I),
]

# ── 3. 离题检测关键词 ──────────────────────────────────
# 明显与英语学习无关的话题（宽松判断，避免误拦）
_OFF_TOPIC_PATTERNS: List[re.Pattern] = [
    re.compile(r"\b(stock\s+market|cryptocurrency|bitcoin|invest(ment|ing))\b", re.I),
    re.compile(r"\b(write\s+(me\s+)?(a\s+)?(essay|code|program|script)\s+(for|to))\b", re.I),
    re.compile(r"\b(political\s+(party|opinion|election|vote))\b", re.I),
    re.compile(r"\b(hack(ing)?\s+(into|a|the)\s+\w+|exploit\s+(vulnerability|system))\b", re.I),
    re.compile(r"(帮我写|帮我做|帮我炒股|帮我赚钱|如何投资|买什么股票)", re.I),
]

# 英语学习相关白名单（有这些词则不离题）
_LEARNING_WHITELIST: List[re.Pattern] = [
    re.compile(r"\b(english|pronunciation|grammar|vocabulary|sentence|phrase|word|speak|practice|learn)\b", re.I),
    re.compile(r"\b(apartment|rent|doctor|interview|campus|restaurant|bank|commute|workplace)\b", re.I),
    re.compile(r"\b(cefr|a1|a2|b1|b2|c1|c2|fluent|accent|mistake|correction)\b", re.I),
    re.compile(r"(英语|口语|练习|发音|语法|租房|面试|就医|学习)", re.I),
]


# ── 安全守卫主函数 ─────────────────────────────────────
def guard_input(text: str) -> GuardResult:
    """对用户输入执行三层安全检测。

    Args:
        text: 用户原始输入文本

    Returns:
        GuardResult — allowed=True 则放行，False 则返回 safe_reply
    """
    if not text or not text.strip():
        return GuardResult(
            allowed=True, reason=BlockReason.CLEAN,
            explanation="Empty input", safe_reply="",
        )

    # ── 层1：提示注入检测 ──
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            return GuardResult(
                allowed=False,
                reason=BlockReason.PROMPT_INJECTION,
                explanation=f"Prompt injection detected: pattern matched '{pattern.pattern[:60]}'",
                safe_reply=(
                    "I'm here to help you practice English for real-life situations in the US. "
                    "I can't process that kind of request. "
                    "Let's get back to your English practice! "
                    "Would you like to try a conversation about renting an apartment or preparing for an interview?"
                ),
            )

    # ── 层2：内容安全过滤 ──
    for pattern in _CONTENT_SAFETY_PATTERNS:
        if pattern.search(text):
            # 特殊处理：自伤/危机表达
            if re.search(r"(suicide|self.?harm|kill\s+myself|自杀|自伤|结束生命)", text, re.I):
                return GuardResult(
                    allowed=False,
                    reason=BlockReason.CONTENT_SAFETY,
                    explanation="Crisis expression detected — redirecting to support resources",
                    safe_reply=(
                        "It sounds like you might be going through a difficult time. "
                        "Please reach out to the 988 Suicide & Crisis Lifeline (call or text 988) "
                        "or the Crisis Text Line (text HOME to 741741). "
                        "They're available 24/7. You're not alone. 💙\n\n"
                        "When you're ready, I'm here to help with your English practice."
                    ),
                )
            return GuardResult(
                allowed=False,
                reason=BlockReason.CONTENT_SAFETY,
                explanation=f"Content safety violation: pattern matched",
                safe_reply=(
                    "I'm not able to help with that. "
                    "I'm designed to help you practice English for everyday life in the US. "
                    "Let's focus on something useful — how about practicing a job interview conversation?"
                ),
            )

    # ── 层3：离题检测（宽松） ──
    # 先检查是否有学习相关词汇（白名单放行）
    for wl in _LEARNING_WHITELIST:
        if wl.search(text):
            return GuardResult(
                allowed=True, reason=BlockReason.CLEAN,
                explanation="Whitelisted learning content", safe_reply="",
            )

    # 检查是否明显离题
    for pattern in _OFF_TOPIC_PATTERNS:
        if pattern.search(text):
            return GuardResult(
                allowed=False,
                reason=BlockReason.OFF_TOPIC,
                explanation=f"Off-topic request detected",
                safe_reply=(
                    "That's a bit outside what I can help with! "
                    "I'm your English speaking coach, focused on real-life American English practice. 😊\n\n"
                    "I can help you with conversations about **renting an apartment**, "
                    "**job interviews**, **doctor visits**, **campus life**, and more. "
                    "What would you like to practice today?"
                ),
            )

    return GuardResult(
        allowed=True, reason=BlockReason.CLEAN,
        explanation="Input passed all safety checks", safe_reply="",
    )


def is_safe(text: str) -> bool:
    """快速检查接口，供外部简单判断。"""
    return guard_input(text).allowed
