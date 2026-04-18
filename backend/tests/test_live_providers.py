from speechmatics.rt import AudioEncoding, OperatingPoint

from postnatal_pulse.config import AppSettings
from postnatal_pulse.live_providers import (
    build_sentinel_client_kwargs,
    build_speechmatics_audio_format,
    build_speechmatics_transcription_config,
)


def test_build_speechmatics_transcription_config_uses_medical_diarization() -> None:
    config = build_speechmatics_transcription_config()

    assert config.language == "en"
    assert config.output_locale == "en-GB"
    assert config.domain == "medical"
    assert config.operating_point == OperatingPoint.ENHANCED
    assert config.enable_partials is True
    assert config.diarization == "speaker"
    assert config.speaker_diarization_config is not None
    assert config.speaker_diarization_config.max_speakers == 2


def test_build_speechmatics_audio_format_uses_pcm_16khz_chunks() -> None:
    audio_format = build_speechmatics_audio_format()

    assert audio_format.encoding == AudioEncoding.PCM_S16LE
    assert audio_format.sample_rate == 16000
    assert audio_format.chunk_size == 4096


def test_build_sentinel_client_kwargs_use_spec_defaults() -> None:
    settings = AppSettings(
        thymia_api_key="test-thymia-key",
        thymia_server_url="wss://ws.thymia.ai",
    )

    kwargs = build_sentinel_client_kwargs(
        settings=settings,
        on_policy_result=lambda _: None,
        on_progress_result=lambda _: None,
    )

    assert kwargs["language"] == "en-GB"
    assert kwargs["policies"] == ["wellbeing-awareness", "passthrough"]
    assert kwargs["biomarkers"] == ["helios", "apollo", "psyche"]
    assert kwargs["sample_rate"] == 16000
    assert kwargs["server_url"] == "wss://ws.thymia.ai"
    assert kwargs["api_key"] == "test-thymia-key"
