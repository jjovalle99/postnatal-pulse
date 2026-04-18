from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TranscriptEntry:
    t: int
    speaker: str
    text: str


@dataclass(frozen=True, slots=True)
class ScenarioFixture:
    id: str
    label: str
    duration_seconds: int
    has_flag: bool
    flag_at_t: int | None
    audio_url: str
    triage_pre_flag: str
    triage_post_flag: str
    confidence: str
    drivers: tuple[str, str, str]
    contributing_signals: tuple[str, ...]
    transcript: tuple[TranscriptEntry, ...]
    flag_kind: str | None


SCENARIO_FIXTURES = {
    "A": ScenarioFixture(
        id="A",
        label="Scenario A — Minimizing exhaustion",
        duration_seconds=240,
        has_flag=True,
        flag_at_t=134,
        audio_url="/assets/tts/scenario-a.wav",
        triage_pre_flag="green",
        triage_post_flag="amber",
        confidence="High",
        drivers=(
            "Voice signals increasing strain and fatigue across the last 90 seconds.",
            "Voice signals reduced enjoyment and engagement when baby and feeding come up.",
            "Spoken words stay reassuring while acoustic stress keeps climbing — the two don’t match.",
        ),
        contributing_signals=("Fatigue", "Anhedonia", "Sleep issues"),
        transcript=(
            TranscriptEntry(
                t=3,
                speaker="Clinician",
                text="Hi Maya, it’s Sister Okafor from the community midwife team. Is now still a good time?",
            ),
            TranscriptEntry(t=9, speaker="Patient", text="Yes, yes, it’s fine. Leo’s just gone down."),
            TranscriptEntry(
                t=16,
                speaker="Clinician",
                text="Lovely. How have the last couple of weeks been?",
            ),
            TranscriptEntry(t=22, speaker="Patient", text="Oh, you know. Busy. But good. We’re getting there."),
            TranscriptEntry(
                t=33,
                speaker="Clinician",
                text="And how’s the sleep going — yours, I mean?",
            ),
            TranscriptEntry(t=40, speaker="Patient", text="It’s alright. He wakes a few times. I manage."),
            TranscriptEntry(
                t=52,
                speaker="Clinician",
                text="A few times a night, or more than that?",
            ),
            TranscriptEntry(
                t=58,
                speaker="Patient",
                text="Probably… every two hours? But honestly, that’s normal isn’t it.",
            ),
            TranscriptEntry(
                t=71,
                speaker="Clinician",
                text="It’s very common. Are you able to rest when he rests?",
            ),
            TranscriptEntry(t=78, speaker="Patient", text="I try. There’s always something. But I’m fine, really."),
            TranscriptEntry(t=92, speaker="Clinician", text="And how’s feeding going?"),
            TranscriptEntry(t=98, speaker="Patient", text="Fine. It’s fine. He feeds well."),
            TranscriptEntry(
                t=108,
                speaker="Clinician",
                text="And in yourself — how are you feeling in yourself?",
            ),
            TranscriptEntry(
                t=116,
                speaker="Patient",
                text="Yeah, good. Tired. But good. Everyone’s tired, aren’t they.",
            ),
            TranscriptEntry(
                t=128,
                speaker="Clinician",
                text="Anything you’ve been finding hard to enjoy lately?",
            ),
            TranscriptEntry(t=134, speaker="Patient", text="I’m fine. Honestly. I’m fine."),
            TranscriptEntry(
                t=142,
                speaker="Clinician",
                text="Okay. I’m going to ask a couple of quick things, just to check in.",
            ),
            TranscriptEntry(t=152, speaker="Patient", text="Sure. Go ahead."),
            TranscriptEntry(
                t=165,
                speaker="Clinician",
                text="Who’s around helping you day to day?",
            ),
            TranscriptEntry(
                t=172,
                speaker="Patient",
                text="My partner’s back at work. My mum comes when she can.",
            ),
            TranscriptEntry(
                t=186,
                speaker="Clinician",
                text="And when you get a moment to yourself, what does that look like?",
            ),
            TranscriptEntry(
                t=194,
                speaker="Patient",
                text="Um… I don’t really. There isn’t really a moment.",
            ),
            TranscriptEntry(
                t=208,
                speaker="Clinician",
                text="Thank you for telling me that. That’s useful to know.",
            ),
        ),
        flag_kind="minimization",
    ),
    "B": ScenarioFixture(
        id="B",
        label="Scenario B — Open distress",
        duration_seconds=210,
        has_flag=True,
        flag_at_t=92,
        audio_url="/assets/tts/scenario-b.wav",
        triage_pre_flag="amber",
        triage_post_flag="red",
        confidence="High",
        drivers=(
            "Voice signals sustained distress and tearfulness in the last 60 seconds.",
            "Spoken content and voice signals are both elevated — consistent, not minimizing.",
            "Low energy and reduced enjoyment reported directly.",
        ),
        contributing_signals=("Distress", "Sleep issues", "Anhedonia", "Fatigue"),
        transcript=(
            TranscriptEntry(t=3, speaker="Clinician", text="Hi Maya — Sister Okafor calling. Is now okay to talk?"),
            TranscriptEntry(t=9, speaker="Patient", text="Yeah… yeah. Sorry. Bit of a rough morning."),
            TranscriptEntry(t=18, speaker="Clinician", text="No need to apologise. What’s made it rough?"),
            TranscriptEntry(
                t=26,
                speaker="Patient",
                text="He was up most of the night. I don’t think I slept at all.",
            ),
            TranscriptEntry(
                t=40,
                speaker="Clinician",
                text="That sounds really hard. Is that every night, or last night in particular?",
            ),
            TranscriptEntry(
                t=49,
                speaker="Patient",
                text="Most nights, if I’m honest. I can’t remember the last full hour.",
            ),
            TranscriptEntry(
                t=65,
                speaker="Clinician",
                text="And in yourself, Maya — how are you feeling?",
            ),
            TranscriptEntry(t=73, speaker="Patient", text="Not great. I’m crying a lot. Little things set me off."),
            TranscriptEntry(t=88, speaker="Clinician", text="Thank you for telling me."),
            TranscriptEntry(t=92, speaker="Patient", text="I just feel like I’m failing him."),
            TranscriptEntry(
                t=104,
                speaker="Clinician",
                text="You’re not failing him. Let me ask a couple of things to help.",
            ),
            TranscriptEntry(t=120, speaker="Patient", text="Okay."),
            TranscriptEntry(
                t=135,
                speaker="Clinician",
                text="Is there anything you’re still enjoying day to day?",
            ),
            TranscriptEntry(t=142, speaker="Patient", text="Not really. Everything feels flat."),
            TranscriptEntry(t=160, speaker="Clinician", text="And who’s around you at the moment?"),
            TranscriptEntry(
                t=168,
                speaker="Patient",
                text="My partner’s back at work. I’m mostly on my own in the day.",
            ),
        ),
        flag_kind="distress",
    ),
    "C": ScenarioFixture(
        id="C",
        label="Scenario C — Stable recovery",
        duration_seconds=200,
        has_flag=False,
        flag_at_t=None,
        audio_url="/assets/tts/scenario-c.wav",
        triage_pre_flag="green",
        triage_post_flag="green",
        confidence="High",
        drivers=(
            "Voice and spoken content concordant across the call.",
            "Adequate support network reported directly.",
            "No sustained elevation in any voice-distress signal.",
        ),
        contributing_signals=(),
        transcript=(
            TranscriptEntry(t=3, speaker="Clinician", text="Hi Maya, Sister Okafor here. How are things?"),
            TranscriptEntry(t=10, speaker="Patient", text="Hi! Yeah, we’re doing okay actually."),
            TranscriptEntry(t=20, speaker="Clinician", text="Lovely to hear. Sleep any better?"),
            TranscriptEntry(
                t=28,
                speaker="Patient",
                text="A bit — he had one five-hour stretch last night.",
            ),
            TranscriptEntry(t=45, speaker="Clinician", text="And you — taking any time for you?"),
            TranscriptEntry(
                t=53,
                speaker="Patient",
                text="My sister took him yesterday and I had a bath. It was amazing.",
            ),
            TranscriptEntry(t=75, speaker="Clinician", text="Feeding going alright?"),
            TranscriptEntry(
                t=82,
                speaker="Patient",
                text="Yeah, he’s putting weight on. The health visitor was happy.",
            ),
            TranscriptEntry(t=105, speaker="Clinician", text="Anything you’re worried about?"),
            TranscriptEntry(
                t=112,
                speaker="Patient",
                text="Not really. Just the usual — am I doing it right, you know.",
            ),
            TranscriptEntry(
                t=130,
                speaker="Clinician",
                text="Completely normal. You’re doing well, Maya.",
            ),
            TranscriptEntry(t=140, speaker="Patient", text="Thanks. I appreciate that."),
        ),
        flag_kind=None,
    ),
}


def get_scenario_fixture(scenario_id: str) -> ScenarioFixture:
    return SCENARIO_FIXTURES[scenario_id]
