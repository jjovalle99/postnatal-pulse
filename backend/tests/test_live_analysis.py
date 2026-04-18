from postnatal_pulse.live_analysis import (
    LiveSpeakerState,
    SpeechmaticsMessage,
    compute_acoustic_strain,
    evaluate_minimization_gate,
    map_agreement_level,
    normalize_speechmatics_message,
)


def test_normalize_speechmatics_message_maps_first_speaker_to_clinician() -> None:
    speaker_state = LiveSpeakerState()
    message: SpeechmaticsMessage = {
        "message": "AddTranscript",
        "metadata": {
            "transcript": "How have you been feeling since the birth?",
            "start_time": 3.2,
        },
        "results": [
            {
                "alternatives": [
                    {
                        "content": "How",
                        "confidence": 0.98,
                        "speaker": "speaker-a",
                    }
                ]
            }
        ],
    }

    transcript_event = normalize_speechmatics_message(message, speaker_state)

    assert transcript_event == {
        "t": 3.2,
        "speaker": "Clinician",
        "text": "How have you been feeling since the birth?",
        "is_final": True,
        "confidence": 0.98,
    }


def test_normalize_speechmatics_message_maps_second_speaker_to_patient() -> None:
    speaker_state = LiveSpeakerState()
    normalize_speechmatics_message(
        SpeechmaticsMessage(
            {
            "message": "AddTranscript",
            "metadata": {"transcript": "Question", "start_time": 1.0},
            "results": [
                {"alternatives": [{"content": "Question", "confidence": 0.9, "speaker": "speaker-a"}]}
            ],
            }
        ),
        speaker_state,
    )

    transcript_event = normalize_speechmatics_message(
        SpeechmaticsMessage(
            {
            "message": "AddPartialTranscript",
            "metadata": {"transcript": "I am fine", "start_time": 2.5},
            "results": [
                {"alternatives": [{"content": "I", "confidence": 0.76, "speaker": "speaker-b"}]}
            ],
            }
        ),
        speaker_state,
    )

    assert transcript_event == {
        "t": 2.5,
        "speaker": "Patient",
        "text": "I am fine",
        "is_final": False,
        "confidence": 0.76,
    }


def test_compute_acoustic_strain_uses_distress_stress_and_negative_affect() -> None:
    strain = compute_acoustic_strain(
        distress=0.5,
        stress=0.4,
        sad=0.3,
        fearful=0.2,
        disgusted=0.1,
    )

    assert strain == 0.49


def test_map_agreement_level_matches_spec_values() -> None:
    assert map_agreement_level("none") == 0.0
    assert map_agreement_level("mild") == 0.33
    assert map_agreement_level("moderate") == 0.66
    assert map_agreement_level("severe") == 1.0
    assert map_agreement_level("unknown") == 0.0


def test_evaluate_minimization_gate_requires_concordance_and_postnatal_cluster() -> None:
    gate_result = evaluate_minimization_gate(
        concordance_scenario="minimization",
        agreement_level="moderate",
        sleep_issues=0.68,
        low_energy=0.62,
        anhedonia=0.52,
    )

    assert gate_result == {
        "kind": "minimization",
        "triggered": True,
        "contributing_signals": ["Sleep issues", "Low energy"],
    }
