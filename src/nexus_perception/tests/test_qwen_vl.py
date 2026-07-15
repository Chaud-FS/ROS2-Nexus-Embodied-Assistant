"""Unit tests for the Qwen-VL client (offline / stub behaviour, no network)."""
import base64

from nexus_perception.qwen_vl_client import QwenVLClient
from PIL import Image


def test_parse_json_strips_code_fence():
    text = '```json\n{"objects": []}\n```'
    assert QwenVLClient._parse_json(text) == {"objects": []}


def test_parse_json_inline():
    text = 'noise {"a": 1} trailing'
    assert QwenVLClient._parse_json(text) == {"a": 1}


def test_parse_json_no_json_raises():
    import pytest
    with pytest.raises(ValueError):
        QwenVLClient._parse_json("there is no json here")


def test_stub_result_has_objects():
    res = QwenVLClient._stub_result()
    assert "objects" in res
    assert isinstance(res["objects"], list)
    assert res["objects"][0]["name"] == "red_cube"


def test_encode_returns_decodable_b64():
    img = Image.new("RGB", (8, 8), color="red")
    b64 = QwenVLClient._encode(img)
    assert isinstance(b64, str)
    decoded = base64.b64decode(b64)
    assert len(decoded) > 0


def test_analyze_returns_stub_without_key():
    client = QwenVLClient(api_key="sk-xxxx")
    res = client.analyze(Image.new("RGB", (8, 8)), prompt="detect objects")
    assert "objects" in res
    assert isinstance(res["objects"], list)
