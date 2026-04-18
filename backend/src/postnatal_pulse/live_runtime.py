import asyncio
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass, field
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import BaseModel
from thymia_sentinel.models import PolicyResult

from postnatal_pulse.live_analysis import (
    compute_acoustic_strain,
    evaluate_minimization_gate,
    map_agreement_level,
)


type JsonScalar = bool | float | int | str | None
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]
type StreamPayload = Mapping[str, object]
type StreamEvent = tuple[str, StreamPayload]


@dataclass(slots=True)
class LiveEventBuffer:
    condition: asyncio.Condition = field(default_factory=asyncio.Condition)
    events: list[StreamEvent] = field(default_factory=list)
    closed: bool = False

    async def publish(self, event_name: str, payload: StreamPayload) -> None:
        async with self.condition:
            self.events.append((event_name, payload))
            self.condition.notify_all()

    async def close(self) -> None:
        async with self.condition:
            self.closed = True
            self.condition.notify_all()

    async def stream(self) -> AsyncIterator[StreamEvent]:
        index = 0
        while True:
            async with self.condition:
                while index >= len(self.events) and not self.closed:
                    await self.condition.wait()
                if index >= len(self.events) and self.closed:
                    return
                next_event = self.events[index]
                index += 1
            yield next_event


@dataclass(slots=True)
class LiveCallRuntime:
    call_id: UUID
    event_buffer: LiveEventBuffer = field(default_factory=LiveEventBuffer)
    current_flag_id: UUID | None = None
    current_triage_state: str = "green"

    async def publish_initial_triage(self) -> None:
        await self.event_buffer.publish(
            "triage",
            {
                "t": 0,
                "state": "green",
                "source": "pre-flag",
                "flag_id": None,
            },
        )

    def _coerce_mapping(self, value: object) -> Mapping[str, object] | None:
        if isinstance(value, Mapping):
            return {
                str(key): item
                for key, item in value.items()
            }
        if isinstance(value, BaseModel):
            return value.model_dump(exclude_none=True)
        return None

    def _float_value(
        self,
        values: Mapping[str, object],
        key: str,
    ) -> float:
        value = values.get(key)
        if isinstance(value, (int, float)):
            return float(value)
        return 0.0

    async def handle_reasoner_result(self, policy_result: PolicyResult) -> None:
        timestamp = float(policy_result["timestamp"])
        result = policy_result["result"]
        biomarker_summary = self._coerce_mapping(result.get("biomarker_summary"))
        if biomarker_summary is None:
            return

        helios = {
            key: value
            for key, value in {
                "distress": biomarker_summary.get("distress"),
                "stress": biomarker_summary.get("stress"),
                "fatigue": biomarker_summary.get("fatigue"),
            }.items()
            if isinstance(value, float)
        }
        if len(helios) > 0:
            await self.event_buffer.publish(
                "biomarker",
                {"t": timestamp, "layer": "helios", "snapshots": helios},
            )

        apollo = {
            key: value
            for key, value in {
                "sleep_issues": biomarker_summary.get("symptom_sleep_issues"),
                "low_energy": biomarker_summary.get("symptom_low_energy"),
                "anhedonia": biomarker_summary.get("symptom_anhedonia"),
            }.items()
            if isinstance(value, float)
        }
        if len(apollo) > 0:
            await self.event_buffer.publish(
                "biomarker",
                {"t": timestamp, "layer": "apollo", "snapshots": apollo},
            )

        psyche = {
            key: value
            for key, value in {
                "sad": biomarker_summary.get("sad"),
                "fearful": biomarker_summary.get("fearful"),
                "disgusted": biomarker_summary.get("disgusted"),
            }.items()
            if isinstance(value, float)
        }
        if len(psyche) > 0:
            await self.event_buffer.publish(
                "biomarker",
                {"t": timestamp, "layer": "psyche", "snapshots": psyche},
            )

        concordance_analysis = self._coerce_mapping(result.get("concordance_analysis"))
        if concordance_analysis is not None:
            await self.event_buffer.publish(
                "concordance_trace",
                {
                    "t": timestamp,
                    "transcript_min": map_agreement_level(
                        str(concordance_analysis.get("agreement_level", "none"))
                    ),
                    "acoustic_strain": compute_acoustic_strain(
                        distress=self._float_value(biomarker_summary, "distress"),
                        stress=self._float_value(biomarker_summary, "stress"),
                        sad=self._float_value(biomarker_summary, "sad"),
                        fearful=self._float_value(biomarker_summary, "fearful"),
                        disgusted=self._float_value(biomarker_summary, "disgusted"),
                    ),
                },
            )
        else:
            await self.event_buffer.publish(
                "concordance_trace",
                {
                    "t": timestamp,
                    "transcript_min": 0.0,
                    "acoustic_strain": compute_acoustic_strain(
                        distress=self._float_value(biomarker_summary, "distress"),
                        stress=self._float_value(biomarker_summary, "stress"),
                        sad=self._float_value(biomarker_summary, "sad"),
                        fearful=self._float_value(biomarker_summary, "fearful"),
                        disgusted=self._float_value(biomarker_summary, "disgusted"),
                    ),
                },
            )

        gate = evaluate_minimization_gate(
            concordance_scenario=str(
                concordance_analysis.get("scenario", "")
                if concordance_analysis is not None
                else ""
            ),
            agreement_level=str(
                concordance_analysis.get("agreement_level", "")
                if concordance_analysis is not None
                else ""
            ),
            sleep_issues=self._float_value(biomarker_summary, "symptom_sleep_issues"),
            low_energy=self._float_value(biomarker_summary, "symptom_low_energy"),
            anhedonia=self._float_value(biomarker_summary, "symptom_anhedonia"),
        )
        concerns = result.get("concerns")
        flags = self._coerce_mapping(result.get("flags"))
        concerns_text = " ".join(concerns) if isinstance(concerns, list) else ""
        contributing_signals = gate["contributing_signals"]
        if not isinstance(contributing_signals, list):
            contributing_signals = []
        distress = self._float_value(biomarker_summary, "distress")
        fatigue = self._float_value(biomarker_summary, "fatigue")
        severe_mismatch = (
            flags is not None and flags.get("severe_mismatch") is True
        )
        high_strain_fallback = distress >= 0.75 and fatigue >= 0.85
        fallback_minimization = (
            "minimization" in concerns_text.lower()
            or "minimises" in concerns_text.lower()
            or "despite" in concerns_text.lower()
            or severe_mismatch
        ) and (
            len(contributing_signals) > 1 or high_strain_fallback
        )
        triggered = gate["triggered"] if isinstance(gate["triggered"], bool) else False
        if triggered or fallback_minimization:
            self.current_flag_id = uuid5(
                NAMESPACE_URL,
                f"postnatal-pulse:{self.call_id}:live-flag",
            )
            await self.event_buffer.publish(
                "flag",
                {
                        "flag_id": str(self.current_flag_id),
                        "kind": "minimization",
                        "t": timestamp,
                        "contributing_signals": contributing_signals,
                    "deterministic_payload": {
                        "source": "live",
                            "agreement_level": str(
                                concordance_analysis.get("agreement_level", "")
                            if concordance_analysis is not None
                            else ""
                        ),
                        "fallback_minimization": fallback_minimization,
                    },
                },
            )
            await self.event_buffer.publish(
                "rationale_done",
                {
                    "flag_id": str(self.current_flag_id),
                    "drivers": [
                        "Voice strain is rising while the spoken content remains reassuring.",
                        "Sleep-related vocal fatigue is elevated in the recent window.",
                        "Acoustic distress remains higher than the transcript suggests.",
                    ],
                    "confidence": "High",
                },
            )
            self.current_triage_state = "amber"
            await self.event_buffer.publish(
                "triage",
                {
                    "t": timestamp,
                    "state": "amber",
                    "source": "post-flag",
                    "flag_id": str(self.current_flag_id),
                },
            )

    async def drain_pending(self) -> list[StreamEvent]:
        return list(self.event_buffer.events)
