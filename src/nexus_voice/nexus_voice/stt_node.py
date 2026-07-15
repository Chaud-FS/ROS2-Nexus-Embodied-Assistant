"""Speech-to-text node.

Providers:
  * mock    -> no microphone; text is injected via the /nexus/voice/text_input topic
                (useful for headless / CI / demos without audio hardware).
  * google  -> uses SpeechRecognition + Google Web Speech API (free, online).
  * whisper -> records via microphone and transcribes with the OpenAI Whisper API.

In all modes a recognized utterance is published to /nexus/voice/text.
"""
from __future__ import annotations

import os
import tempfile
from typing import Optional

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from std_srvs.srv import Trigger


class STTNode(Node):
    def __init__(self) -> None:
        super().__init__("stt_node")

        self.declare_parameter("provider", "mock")
        self.declare_parameter("language", "en-US")
        self.declare_parameter("openai_api_key", "")
        self.declare_parameter("text_topic", "/nexus/voice/text")
        self.declare_parameter("input_topic", "/nexus/voice/text_input")
        self.declare_parameter("listen_service", "/nexus/voice/listen")

        self.provider = self.get_parameter("provider").value
        self.language = self.get_parameter("language").value
        self.openai_api_key = (
            self.get_parameter("openai_api_key").value
            or os.environ.get("OPENAI_API_KEY", "")
        )
        text_topic = self.get_parameter("text_topic").value
        input_topic = self.get_parameter("input_topic").value
        listen_srv = self.get_parameter("listen_service").value

        self.pub = self.create_publisher(String, text_topic, 10)
        self.create_subscription(String, input_topic, self._on_injected, 10)
        self.create_service(Trigger, listen_srv, self._on_listen)

        self.get_logger().info(
            f"STT ready (provider={self.provider}). "
            f"Inject text on '{input_topic}' or call '{listen_srv}'."
        )

    # ---------------- callbacks ---------------- #
    def _on_injected(self, msg: String) -> None:
        self.get_logger().info(f"Heard (injected): {msg.data}")
        self.pub.publish(msg)

    def _on_listen(self, _req: Trigger.Request, resp: Trigger.Response):
        text = self._recognize()
        if text:
            self.pub.publish(String(data=text))
            resp.success = True
            resp.message = text
        else:
            resp.success = False
            resp.message = "no speech recognized"
        return resp

    # ---------------- recognition ---------------- #
    def _recognize(self) -> Optional[str]:
        if self.provider == "mock":
            self.get_logger().warn("STT provider=mock: call ignored (no mic).")
            return None
        try:
            import speech_recognition as sr
        except ImportError:
            self.get_logger().error("speech_recognition not installed.")
            return None

        recognizer = sr.Recognizer()
        try:
            with sr.Microphone() as source:
                self.get_logger().info("Listening...")
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=8)
        except Exception as exc:  # noqa: BLE001
            self.get_logger().error(f"Mic error: {exc}")
            return None

        try:
            if self.provider == "google":
                return recognizer.recognize_google(audio, language=self.language)
            if self.provider == "whisper":
                return self._whisper(audio)
        except Exception as exc:  # noqa: BLE001
            self.get_logger().error(f"Recognition failed: {exc}")
        return None

    def _whisper(self, audio) -> Optional[str]:
        import openai

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio.get_wav_data())
            path = f.name
        client = openai.OpenAI(api_key=self.openai_api_key)
        with open(path, "rb") as af:
            resp = client.audio.transcriptions.create(model="whisper-1", file=af)
        os.remove(path)
        return resp.text


def main(args: Optional[list] = None) -> None:
    rclpy.init(args=args)
    node = STTNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
