"""Client for the Qwen-VL multimodal model.

Supports two backends:
  * DashScope (`qwen-vl-max` / `qwen-vl-plus`) via the DashScope multimodal API.
  * Any OpenAI-compatible vision endpoint (e.g. a local vLLM serving Qwen-VL)
    using the chat/completions vision message format.

The client sends one RGB frame plus a prompt and expects a structured JSON
description of the scene back (object labels + 2D bounding boxes).
"""
from __future__ import annotations

import base64
import json
import logging
import time
from io import BytesIO
from typing import Any, Dict, List, Optional

import requests
from PIL import Image

logger = logging.getLogger(__name__)


class QwenVLClient:
    """Thin synchronous wrapper around Qwen-VL."""

    DASHSCOPE_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"

    def __init__(
        self,
        api_key: str,
        model: str = "qwen-vl-max",
        base_url: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url or self.DASHSCOPE_URL
        self.timeout = timeout

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def analyze(
        self,
        image: Image.Image,
        prompt: str = (
            "You are the vision system of a tabletop robot arm. "
            "Detect the graspable objects on the table. "
            "Respond ONLY with JSON of the form: "
            '{"scene_description": str, '
            '"objects": [{"name": str, "confidence": float, '
            '"bbox": [x1, y1, x2, y2]}]} '
            "where bbox is in pixel coordinates of the image."
        ),
    ) -> Dict[str, Any]:
        """Run VL analysis and return a parsed dict."""
        if not self.api_key or self.api_key.startswith("sk-xxxx"):
            logger.warning("No valid API key configured -> returning stub result.")
            return self._stub_result()

        try:
            raw = self._call_model(image, prompt)
            return self._parse_json(raw)
        except Exception as exc:  # noqa: BLE001 - keep perception resilient
            logger.error("Qwen-VL call failed: %s", exc)
            return self._stub_result()

    # ------------------------------------------------------------------ #
    # Backend specifics
    # ------------------------------------------------------------------ #
    def _call_model(self, image: Image.Image, prompt: str) -> str:
        if "dashscope" in self.base_url:
            return self._call_dashscope(image, prompt)
        return self._call_openai(image, prompt)

    def _call_dashscope(self, image: Image.Image, prompt: str) -> str:
        b64 = self._encode(image)
        payload = {
            "model": self.model,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"image": f"data:image/jpeg;base64,{b64}"},
                            {"text": prompt},
                        ],
                    }
                ]
            },
            "parameters": {"result_format": "message"},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        resp = requests.post(
            self.base_url, json=payload, headers=headers, timeout=self.timeout
        )
        resp.raise_for_status()
        data = resp.json()
        return data["output"]["choices"][0]["message"]["content"][0]["text"]

    def _call_openai(self, image: Image.Image, prompt: str) -> str:
        b64 = self._encode(image)
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{b64}"
                            },
                        },
                    ],
                }
            ],
            "max_tokens": 1024,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        resp = requests.post(
            self.base_url, json=payload, headers=headers, timeout=self.timeout
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _encode(image: Image.Image) -> str:
        buf = BytesIO()
        image.convert("RGB").save(buf, format="JPEG", quality=85)
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    @staticmethod
    def _parse_json(text: str) -> Dict[str, Any]:
        # Strip code fences / prose that may wrap the JSON.
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end == -1:
            raise ValueError(f"No JSON found in model output: {text!r}")
        return json.loads(text[start : end + 1])

    @staticmethod
    def _stub_result() -> Dict[str, Any]:
        """Fallback when no model is reachable (keeps the demo runnable)."""
        return {
            "scene_description": "STUB: offline perception (no model configured).",
            "objects": [
                {"name": "red_cube", "confidence": 0.5, "bbox": [300, 200, 340, 260]},
                {"name": "blue_box", "confidence": 0.5, "bbox": [320, 230, 360, 290]},
            ],
        }
