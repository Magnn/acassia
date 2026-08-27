import base64

from tts.audio_engine import AudioEngine


class _GeminiResponse:
    status_code = 200
    text = ""

    def json(self):
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"inlineData": {"data": base64.b64encode(b"audio").decode("ascii")}}
                        ]
                    }
                }
            ]
        }


def test_gemini_tts_uses_selected_voice_style_and_speed(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured.update(kwargs["json"])
        return _GeminiResponse()

    monkeypatch.setattr("tts.audio_engine.requests.post", fake_post)
    audio = AudioEngine()._chamar_gemini_tts(
        "Texto de teste",
        voice_name="Kore",
        style=0.8,
        speed=1.3,
    )

    assert audio == b"audio"
    generation = captured["generationConfig"]
    assert generation["speechConfig"]["voiceConfig"]["prebuiltVoiceConfig"]["voiceName"] == "Kore"
    prompt = captured["contents"][0]["parts"][0]["text"]
    assert "expressivo" in prompt
    assert "mais rápido" in prompt
