# -*- coding: utf-8 -*-
"""课前四维度水平测评：听 / 说 / 读 / 写。"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from config import CEFR_LEVELS, CEFR_NUMERIC
from core.llm_client import LLMClient, MockLLMClient
from core.speech import SpeechService


@dataclass
class PlacementResult:
    """测评结果。"""
    scores: Dict[str, int] = field(default_factory=dict)  # listening/speaking/reading/writing
    cefr: str = "B1"
    rationale: str = ""
    subscores: Dict[str, Any] = field(default_factory=dict)


# ── 题库 ──────────────────────────────────────────────
QUESTIONS: Dict[str, List[Dict[str, Any]]] = {
    "listening": [
        {
            "id": "l1", "type": "mc",
            "prompt": "You hear: 'I'd like to make an appointment for next Tuesday.' What does the speaker want to do?",
            "audio_text": "I'd like to make an appointment for next Tuesday.",
            "options": ["Schedule a meeting", "Cancel a reservation", "Buy a product", "File a complaint"],
            "correct": 0,
        },
        {
            "id": "l2", "type": "mc",
            "prompt": "You hear: 'The lease is for 12 months with a one-month deposit.' What are the lease terms?",
            "audio_text": "The lease is for 12 months with a one-month deposit.",
            "options": ["6 months, no deposit", "12 months, one month deposit", "1 month, free", "12 months, no deposit"],
            "correct": 1,
        },
    ],
    "reading": [
        {
            "id": "r1", "type": "mc",
            "prompt": "Read: 'Please bring two forms of identification and your insurance card to your appointment.' What should you bring?",
            "options": ["Just your ID", "Two IDs and insurance card", "Only insurance card", "Nothing"],
            "correct": 1,
        },
        {
            "id": "r2", "type": "mc",
            "prompt": "Read: 'The position requires experience in project management and fluency in English.' What is required?",
            "options": ["Only English fluency", "Only project management", "Both experience and English", "Neither"],
            "correct": 2,
        },
    ],
    "speaking": [
        {
            "id": "s1", "type": "open",
            "prompt": "Please introduce yourself in 2-3 sentences (name, occupation, and why you're learning English).",
        },
        {
            "id": "s2", "type": "open",
            "prompt": "Describe a situation where you needed to use English. What happened and how did you handle it?",
        },
    ],
    "writing": [
        {
            "id": "w1", "type": "open",
            "prompt": "Write a short email (2-3 sentences) to a landlord asking about an available apartment.",
        },
        {
            "id": "w2", "type": "open",
            "prompt": "Write 2-3 sentences about your typical day at work or school.",
        },
    ],
}


class PlacementAssessor:
    """四维度测评器。"""

    def __init__(self, llm: Optional[LLMClient] = None, speech: Optional[SpeechService] = None) -> None:
        self.llm = llm or MockLLMClient()
        self.speech = speech

    def get_questions(self, dimension: str) -> List[Dict[str, Any]]:
        """获取某维度的题目。"""
        return QUESTIONS.get(dimension, [])

    def score_mc(self, question: Dict[str, Any], selected: int) -> int:
        """选择题评分。"""
        return 100 if selected == question.get("correct") else 40

    def score_open(self, dimension: str, question: Dict[str, Any], answer: str) -> int:
        """开放题评分（说/写）。在线用 LLM，离线用启发式。"""
        if not answer.strip():
            return 30

        # 启发式评分（离线 / 兜底）
        word_count = len(answer.split())
        sentence_count = max(answer.count(".") + answer.count("!") + answer.count("?"), 1)

        base = 50
        # 长度加分
        if word_count >= 20:
            base += 20
        elif word_count >= 10:
            base += 10
        elif word_count >= 5:
            base += 5
        # 句子多样性
        if sentence_count >= 3:
            base += 10
        elif sentence_count >= 2:
            base += 5
        # 简单错误检测
        lower = answer.lower()
        common_errors = ["i no", "is no", "he go", "she go", "two book", "open the light",
                         "depend of", "more better", "is available?"]
        errors = sum(1 for e in common_errors if e in lower)
        base -= errors * 8

        return max(30, min(100, base))

    def assess(self, profile, answers: Dict[str, Any]) -> PlacementResult:
        """综合评分。answers = {question_id: selected_index 或 answer_text}。"""
        scores: Dict[str, int] = {}

        for dimension in ["listening", "speaking", "reading", "writing"]:
            questions = self.get_questions(dimension)
            if not questions:
                scores[dimension] = 60
                continue

            dim_scores: List[int] = []
            for q in questions:
                qid = q["id"]
                ans = answers.get(qid)
                if ans is None:
                    dim_scores.append(40)
                elif q["type"] == "mc":
                    dim_scores.append(self.score_mc(q, int(ans)))
                else:
                    dim_scores.append(self.score_open(dimension, q, str(ans)))

            scores[dimension] = sum(dim_scores) // len(dim_scores)

        # CEFR 推断
        avg = sum(scores.values()) / len(scores) if scores else 50
        cefr = self._score_to_cefr(avg)

        # 弱项分析
        weakest = min(scores, key=scores.get) if scores else "speaking"
        strongest = max(scores, key=scores.get) if scores else "reading"

        rationale = (
            f"Overall average: {avg:.0f}/100 → CEFR {cefr}. "
            f"Strongest skill: {strongest} ({scores.get(strongest, 0)}). "
            f"Weakest skill: {weakest} ({scores.get(weakest, 0)}) — recommend extra focus."
        )

        return PlacementResult(
            scores=scores, cefr=cefr, rationale=rationale,
            subscores={"average": round(avg, 1), "weakest": weakest, "strongest": strongest},
        )

    def _score_to_cefr(self, score: float) -> str:
        """分数转 CEFR。"""
        if score >= 90:
            return "C1"
        if score >= 75:
            return "B2"
        if score >= 60:
            return "B1"
        if score >= 45:
            return "A2"
        return "A1"
