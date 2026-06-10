from app.security import clamp_code, redact_secrets


def test_redact_secrets_masks_api_keys() -> None:
    result = redact_secrets("OPENAI_API_KEY='sk-abcdefghijklmnopqrstuvwxyz123456'")

    assert result.count == 1
    assert "sk-abcdefghijklmnopqrstuvwxyz123456" not in result.text
    assert "REDACTED" in result.text


def test_clamp_code_marks_truncated_input() -> None:
    text, truncated = clamp_code("abcdef", 3)

    assert truncated is True
    assert text.startswith("abc")
    assert "TRUNCATED" in text

