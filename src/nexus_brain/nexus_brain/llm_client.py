"""Minimal LLM client supporting DashScope (Qwen) and OpenAI-compatible APIs."""
from __future__ import annotations

import json
import logging
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are the decision brain of a 6-DOF tabletop robot arm called Nexus. "
    "You receive a natural-language instruction and a structured description of the "
    "current scene (object names, poses, joint state). You must output a single "
    "executable plan as JSON of the form: "
    '{"intent": str, '
    '"steps": [{"action": "move_to|grasp|release|home|wait", '
    '"target": str, "frame": "base_link", "timeout": float}], '
    '"rationale": str}. '
    "Targets must reference object names from the scene or 'home'. "
    "Respond with ONLY the JSON object."
)


class LLMClient:
    def __init__(
        self,
        api_key: str,
        model: str = "qwen-plus",
        base_url: Optional[str] = None,
        timeout: float = 60.0,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.timeout = timeout

    def chat(self, user_prompt: str, system: str = SYSTEM_PROMPT,
             json_mode: bool = True) -> str:
        if not self.api_key or self.api_key.startswith("sk-xxxx"):
            logger.warning("No valid LLM API key -> returning stub plan text.")
            return self._stub(user_prompt)

        if self.base_url and "dashscope" not in self.base_url:
            return self._openai_chat(user_prompt, system, json_mode)
        return self._dashscope_chat(user_prompt, system)

    # ---------------- DashScope (Qwen text) ---------------- #
    def _dashscope_chat(self, user_prompt: str, system: str) -> str:
        url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        payload = {
            "model": self.model,
            "input": {
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_prompt},
                ]
            },
            "parameters": {"result_format": "message"},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        try:
            return data["output"]["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            return data.get("output", {}).get("text", "")

    # ---------------- OpenAI-compatible ---------------- #
    def _openai_chat(self, user_prompt: str, system: str, json_mode: bool) -> str:
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        payload: dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    @staticmethod
    def _stub(user_prompt: str) -> str:
        lp = user_prompt.lower()
        if "pick" in lp or "grasp" in lp:
            target = "red_cube" if "red" in lp else "blue_box"
            return json.dumps({
                "intent": "pick_and_place",
                "steps": [
                    {"action": "move_to", "target": target, "frame": "base_link", "timeout": 8.0},
                    {"action": "grasp", "target": target, "frame": "base_link", "timeout": 4.0},
                    {"action": "move_to", "target": "home", "frame": "base_link", "timeout": 8.0},
                    {"action": "release", "target": "home", "frame": "base_link", "timeout": 3.0},
                ],
                "rationale": "STUB: offline plan (no LLM key configured).",
            })
        return json.dumps({
            "intent": "unknown",
            "steps": [{"action": "wait", "target": "", "frame": "base_link", "timeout": 1.0}],
            "rationale": "STUB: could not interpret command.",
        })
