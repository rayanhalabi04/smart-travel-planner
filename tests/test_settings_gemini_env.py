from app.config import Settings


def test_settings_accepts_gemini_env_names(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "GEMINI_API_KEY=test-key",
                "CHEAP_MODEL_NAME=gemini-2.5-flash-lite",
                "STRONG_MODEL_NAME=gemini-2.5-flash",
            ]
        ),
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)

    assert settings.gemini_api_key == "test-key"
    assert settings.cheap_model_name == "gemini-2.5-flash-lite"
    assert settings.strong_model_name == "gemini-2.5-flash"
    assert settings.resolved_cheap_model == "gemini-2.5-flash-lite"
    assert settings.resolved_strong_model == "gemini-2.5-flash"
