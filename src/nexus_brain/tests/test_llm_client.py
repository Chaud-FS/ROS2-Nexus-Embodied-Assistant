"""Unit tests for the LLM client (offline / stub behaviour, no network)."""
import json

from nexus_brain.llm_client import LLMClient, SYSTEM_PROMPT


def test_system_prompt_describes_plan_shape():
    assert "steps" in SYSTEM_PROMPT
    assert "move_to" in SYSTEM_PROMPT
    assert "grasp" in SYSTEM_PROMPT
    assert "release" in SYSTEM_PROMPT


def test_stub_pick_red_cube():
    text = LLMClient._stub("please pick up the red cube")
    data = json.loads(text)
    assert data["intent"] == "pick_and_place"
    actions = [s["action"] for s in data["steps"]]
    assert "grasp" in actions and "release" in actions
    assert any(s["target"] == "red_cube" for s in data["steps"])


def test_stub_pick_blue_box():
    text = LLMClient._stub("grasp the blue box")
    data = json.loads(text)
    assert any(s["target"] == "blue_box" for s in data["steps"])


def test_stub_unknown_command():
    text = LLMClient._stub("do something weird")
    data = json.loads(text)
    assert data["intent"] == "unknown"
    assert data["steps"][0]["action"] == "wait"


def test_chat_falls_back_to_stub_without_key():
    client = LLMClient(api_key="sk-xxxx", model="qwen-plus")
    out = client.chat("pick up the blue box")
    data = json.loads(out)
    assert data["intent"] == "pick_and_place"
