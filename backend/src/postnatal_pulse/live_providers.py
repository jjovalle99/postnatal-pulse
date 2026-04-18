from collections.abc import Callable

from speechmatics.rt import (
    AudioEncoding,
    AudioFormat,
    OperatingPoint,
    SpeakerDiarizationConfig,
    TranscriptionConfig,
)
from thymia_sentinel.models import PolicyResult, ProgressResult

from postnatal_pulse.config import AppSettings


def build_speechmatics_transcription_config() -> TranscriptionConfig:
    return TranscriptionConfig(
        language="en",
        operating_point=OperatingPoint.ENHANCED,
        output_locale="en-GB",
        domain="medical",
        enable_partials=True,
        diarization="speaker",
        speaker_diarization_config=SpeakerDiarizationConfig(max_speakers=2),
    )


def build_speechmatics_audio_format() -> AudioFormat:
    return AudioFormat(
        encoding=AudioEncoding.PCM_S16LE,
        sample_rate=16000,
        chunk_size=4096,
    )


def build_sentinel_client_kwargs(
    settings: AppSettings,
    on_policy_result: Callable[[PolicyResult], None],
    on_progress_result: Callable[[ProgressResult], None],
) -> dict[str, object]:
    return {
        "language": "en-GB",
        "policies": ["wellbeing-awareness", "passthrough"],
        "biomarkers": ["helios", "apollo", "psyche"],
        "on_policy_result": on_policy_result,
        "on_progress_result": on_progress_result,
        "progress_updates_frequency": 1.0,
        "sample_rate": 16000,
        "server_url": settings.thymia_server_url,
        "api_key": settings.thymia_api_key,
    }
