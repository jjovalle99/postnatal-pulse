import asyncio
from collections.abc import Mapping
from uuid import uuid4

from thymia_sentinel.models import ReasonerBiomarkerSummary

from postnatal_pulse.live_runtime import LiveCallRuntime, LiveEventBuffer


async def test_live_event_buffer_streams_published_events_in_order() -> None:
    buffer = LiveEventBuffer()
    consumed: list[tuple[str, Mapping[str, object]]] = []

    async def consume() -> None:
        async for event_name, payload in buffer.stream():
            consumed.append((event_name, payload))

    consumer = asyncio.create_task(consume())
    await buffer.publish("triage", {"state": "green"})
    await buffer.publish("end", {"call_id": "call-1"})
    await buffer.close()
    await consumer

    assert consumed == [
        ("triage", {"state": "green"}),
        ("end", {"call_id": "call-1"}),
    ]


async def test_live_call_runtime_emits_events_from_reasoner_result() -> None:
    runtime = LiveCallRuntime(call_id=uuid4())

    await runtime.publish_initial_triage()
    await runtime.handle_reasoner_result(
        {
            "type": "POLICY_RESULT",
            "policy": "wellbeing-awareness",
            "policy_name": "wellbeing-awareness",
            "triggered_at_turn": 3,
            "timestamp": 14.5,
            "result": {
                "biomarker_summary": {
                    "distress": 0.61,
                    "stress": 0.45,
                    "fatigue": 0.66,
                    "sad": 0.2,
                    "fearful": 0.1,
                    "disgusted": 0.05,
                    "symptom_sleep_issues": 0.7,
                    "symptom_low_energy": 0.64,
                    "symptom_anhedonia": 0.41,
                },
                "concordance_analysis": {
                    "scenario": "minimization",
                    "agreement_level": "moderate",
                },
                "flags": {
                    "suicidal_content": False,
                },
            },
        }
    )

    drained = await runtime.drain_pending()

    assert drained[0] == ("triage", {"t": 0, "state": "green", "source": "pre-flag", "flag_id": None})
    assert ("biomarker", {"t": 14.5, "layer": "helios", "snapshots": {"distress": 0.61, "stress": 0.45, "fatigue": 0.66}}) in drained
    assert ("biomarker", {"t": 14.5, "layer": "apollo", "snapshots": {"sleep_issues": 0.7, "low_energy": 0.64, "anhedonia": 0.41}}) in drained
    assert ("biomarker", {"t": 14.5, "layer": "psyche", "snapshots": {"sad": 0.2, "fearful": 0.1, "disgusted": 0.05}}) in drained
    assert ("concordance_trace", {"t": 14.5, "transcript_min": 0.66, "acoustic_strain": 0.51}) in drained
    assert any(event_name == "flag" for event_name, _ in drained)
    assert any(event_name == "rationale_done" for event_name, _ in drained)
    assert any(
        event_name == "triage" and payload["state"] == "amber"
        for event_name, payload in drained
    )


async def test_live_call_runtime_uses_minimization_concerns_as_fallback_gate() -> None:
    runtime = LiveCallRuntime(call_id=uuid4())

    await runtime.publish_initial_triage()
    await runtime.handle_reasoner_result(
        {
            "type": "POLICY_RESULT",
            "policy": "wellbeing-awareness",
            "policy_name": "wellbeing-awareness",
            "triggered_at_turn": 8,
            "timestamp": 26.0,
            "result": {
                "concerns": [
                    "High distress despite the patient saying they are fine.",
                    "Potential minimization of significant symptoms.",
                ],
                "flags": {
                    "severe_mismatch": True,
                    "suicidal_content": False,
                },
                "biomarker_summary": {
                    "distress": 0.78,
                    "stress": 0.52,
                    "fatigue": 0.99,
                    "sad": 0.85,
                    "fearful": 0.12,
                    "disgusted": 0.08,
                    "symptom_sleep_issues": 0.71,
                    "symptom_low_energy": 0.66,
                    "symptom_anhedonia": 0.48,
                },
            },
        }
    )

    drained = await runtime.drain_pending()

    assert any(event_name == "flag" for event_name, _ in drained)
    assert any(
        event_name == "triage" and payload["state"] == "amber"
        for event_name, payload in drained
    )


async def test_live_call_runtime_accepts_pydantic_biomarker_summary_payload() -> None:
    runtime = LiveCallRuntime(call_id=uuid4())

    await runtime.publish_initial_triage()
    await runtime.handle_reasoner_result(
        {
            "type": "POLICY_RESULT",
            "policy": "wellbeing-awareness",
            "policy_name": "wellbeing-awareness",
            "triggered_at_turn": 12,
            "timestamp": 33.0,
            "result": {
                "concerns": ["Possible minimization of symptoms"],
                "flags": {"severe_mismatch": True},
                "biomarker_summary": ReasonerBiomarkerSummary(
                    distress=0.86,
                    stress=0.55,
                    fatigue=1.0,
                    sad=0.93,
                    fearful=0.08,
                    disgusted=0.03,
                    symptom_sleep_issues=0.72,
                    symptom_low_energy=0.69,
                    symptom_anhedonia=0.44,
                ),
            },
        }
    )

    drained = await runtime.drain_pending()

    assert any(event_name == "biomarker" and payload["layer"] == "apollo" for event_name, payload in drained)
    assert any(event_name == "flag" for event_name, _ in drained)


async def test_live_call_runtime_flags_when_minimization_concern_has_high_distress_and_fatigue() -> None:
    runtime = LiveCallRuntime(call_id=uuid4())

    await runtime.publish_initial_triage()
    await runtime.handle_reasoner_result(
        {
            "type": "POLICY_RESULT",
            "policy": "wellbeing-awareness",
            "policy_name": "wellbeing-awareness",
            "triggered_at_turn": 20,
            "timestamp": 45.0,
            "result": {
                "concerns": [
                    "Patient minimises symptoms despite biomarker evidence",
                    "High distress and severe fatigue remain present",
                ],
                "flags": {"severe_mismatch": True},
                "biomarker_summary": {
                    "distress": 0.77,
                    "stress": 0.42,
                    "fatigue": 0.98,
                    "sad": 0.91,
                },
            },
        }
    )

    drained = await runtime.drain_pending()

    assert any(event_name == "flag" for event_name, _ in drained)
