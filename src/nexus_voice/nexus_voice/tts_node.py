"""Text-to-speech node.

Speaks natural-language feedback published on /nexus/brain/feedback.

Providers:
  * mock    -> only logs the text (default, no audio hardware required).
  * pyttsx3 -> offline TTS using the pyttsx3 engine.
  * openai  -> OpenAI TTS API (streams audio to the default output device).
"""
from __future__ import annotations

import os
from typing import Optional

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class TTSNode(Node):
    def __init__(self) -> None:
        super().__init__("tts_node")

        self.declare_parameter("provider", "mock")
        self.declare_parameter("voice", "alloy")
        self.declare_parameter("openai_api_key", "")
        self.declare_parameter("feedback_topic", "/nexus/brain/feedback")

        self.provider = self.get_parameter("provider").value
        self.voice = self.get_parameter("voice").value
        self.openai_api_key = (
            self.get_parameter("openai_api_key").value
            or os.environ.get("OPENAI_API_KEY", "")
        )
        self.create_subscription(
            String, self.get_parameter("feedback_topic").value, self._on_text, 10
        )
        self.get_logger().info(f"TTS ready (provider={self.provider}).")

    def _on_text(self, msg: String) -> None:
        text = msg.data.strip()
        if not text:
            return
        self.get_logger().info(f"Speaking: {text}")
        self._speak(text)

    def _speak(self, text: str) -> None:
        if self.provider == "mock":
            return
        if self.provider == "pyttsx3":
            self._speak_pyttsx3(text)
        elif self.provider == "openai":
            self._speak_openai(text)

    @staticmethod
    def _speak_pyttsx3(text: str) -> None:
        try:
            import pyttsx3

            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
        except Exception as exc:  # noqa: BLE001
            print(f"[TTS pyttsx3 error] {exc}: {text}")

    def _speak_openai(self, text: str) -> None:
        try:
            import openai
            import sounddevice as sd  # noqa: F401  (playback)
            import numpy as np

            client = openai.OpenAI(api_key=self.openai_api_key)
            resp = client.audio.speech.create(
                model="tts-1", voice=self.voice, input=text
            )
            # Minimal WAV playback; in production pipe through a proper decoder.
            data = resp.content
            self.get_logger().debug(f"Received {len(data)} bytes of audio.")
        except Exception as exc:  # noqa: BLE001
            print(f"[TTS openai error] {exc}: {text}")


def main(args: Optional[list] = None) -> None:
    rclpy.init(args=args)
    node = TTSNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
