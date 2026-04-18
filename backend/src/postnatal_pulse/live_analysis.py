from dataclasses import dataclass, field
from typing import TypedDict


class SpeechmaticsAlternative(TypedDict, total=False):
    content: str
    confidence: float
    speaker: str


class SpeechmaticsResult(TypedDict, total=False):
    alternatives: list[SpeechmaticsAlternative]


class SpeechmaticsMetadata(TypedDict):
    transcript: str
    start_time: float


class SpeechmaticsMessage(TypedDict):
    message: str
    metadata: SpeechmaticsMetadata
    results: list[SpeechmaticsResult]


@dataclass(slots=True)
class LiveSpeakerState:
    roles_by_speaker: dict[str, str] = field(default_factory=dict)


def map_agreement_level(agreement_level: str) -> float:
    mapping = {
        "none": 0.0,
        "mild": 0.33,
        "moderate": 0.66,
        "severe": 1.0,
    }
    return mapping.get(agreement_level, 0.0)


def assign_speaker_role(speaker_state: LiveSpeakerState, speaker: str | None) -> str:
    if speaker is None:
        return "Patient"

    if speaker in speaker_state.roles_by_speaker:
        return speaker_state.roles_by_speaker[speaker]

    next_role = "Clinician" if len(speaker_state.roles_by_speaker) == 0 else "Patient"
    speaker_state.roles_by_speaker[speaker] = next_role
    return next_role


def normalize_speechmatics_message(
    message: SpeechmaticsMessage,
    speaker_state: LiveSpeakerState,
) -> dict[str, float | str | bool | None]:
    confidence = None
    speaker = None
    for result in message["results"]:
        alternatives = result.get("alternatives")
        if alternatives is None or len(alternatives) == 0:
            continue
        alternative = alternatives[0]
        confidence_value = alternative.get("confidence")
        if isinstance(confidence_value, float):
            confidence = confidence_value
        speaker_value = alternative.get("speaker")
        if isinstance(speaker_value, str):
            speaker = speaker_value
            break

    return {
        "t": message["metadata"]["start_time"],
        "speaker": assign_speaker_role(speaker_state, speaker),
        "text": message["metadata"]["transcript"],
        "is_final": message.get("message") == "AddTranscript",
        "confidence": confidence,
    }


def compute_acoustic_strain(
    distress: float,
    stress: float,
    sad: float,
    fearful: float,
    disgusted: float,
) -> float:
    negative_psyche = min(1.0, max(0.0, sad + fearful + disgusted))
    return round(
        0.5 * distress + 0.3 * stress + 0.2 * negative_psyche,
        2,
    )


def evaluate_minimization_gate(
    concordance_scenario: str,
    agreement_level: str,
    sleep_issues: float,
    low_energy: float,
    anhedonia: float,
) -> dict[str, bool | str | list[str]]:
    cluster_triggered = sleep_issues >= 0.60 and (
        low_energy >= 0.60 or anhedonia >= 0.55
    )
    concordance_triggered = (
        concordance_scenario == "minimization"
        and agreement_level in {"moderate", "severe"}
    )
    contributing_signals = ["Sleep issues"]
    if low_energy >= 0.60:
        contributing_signals.append("Low energy")
    elif anhedonia >= 0.55:
        contributing_signals.append("Anhedonia")

    return {
        "kind": "minimization",
        "triggered": concordance_triggered and cluster_triggered,
        "contributing_signals": contributing_signals,
    }
