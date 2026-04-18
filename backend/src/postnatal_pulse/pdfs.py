from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from hmac import compare_digest, new as new_hmac
import os
from pathlib import Path
from uuid import UUID, uuid4

from jinja2 import Environment, FileSystemLoader, select_autoescape

from postnatal_pulse.config import BACKEND_DIR
from postnatal_pulse.fixtures import ScenarioFixture, TranscriptEntry


TEMPLATE_DIR = BACKEND_DIR / 'templates'
PDF_STORAGE_DIR = BACKEND_DIR / '.generated'
PATIENT_NAME = 'Maya Patel'
PATIENT_AGE = 29
PATIENT_WEEKS = '6 weeks postpartum'
PATIENT_BABY = 'Leo Patel, 6 weeks'
CLINICIAN_NAME = 'Sister J. Okafor'
PROBE_QUESTIONS = (
    'How have you been sleeping when the baby sleeps?',
    'Are you still enjoying anything day to day?',
    'Who is helping you at the moment?',
)


@dataclass(frozen=True, slots=True)
class PdfArtifact:
    id: UUID
    call_id: UUID
    storage_path: Path
    generated_at: datetime
    recipient_phone: str | None = None
    sms_id: str | None = None
    sms_dispatched_at: datetime | None = None
    sms_delivered_at: datetime | None = None
    signed_download_url: str | None = None


@dataclass(slots=True)
class PdfRegistry:
    pdfs: dict[UUID, PdfArtifact] = field(default_factory=dict)


def get_pdf_environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(enabled_extensions=('html',)),
    )


def get_transcript_excerpt(scenario: ScenarioFixture) -> tuple[TranscriptEntry, ...]:
    if scenario.flag_at_t is None:
        return scenario.transcript[:6]

    return tuple(
        entry
        for entry in scenario.transcript
        if scenario.flag_at_t - 24 <= entry.t <= scenario.flag_at_t + 60
    )


def sign_pdf_download(pdf_id: UUID, exp: int, secret: str) -> str:
    return new_hmac(
        secret.encode('utf-8'),
        f'{pdf_id}|{exp}'.encode('utf-8'),
        sha256,
    ).hexdigest()


def verify_pdf_download_signature(
    pdf_id: UUID,
    exp: int,
    signature: str,
    secret: str,
) -> bool:
    expected_signature = sign_pdf_download(pdf_id, exp, secret)
    return compare_digest(signature, expected_signature)


def create_signed_download_url(pdf_id: UUID, secret: str) -> str:
    exp = int((datetime.now(UTC) + timedelta(days=7)).timestamp())
    sig = sign_pdf_download(pdf_id, exp, secret)
    return f'/api/pdfs/{pdf_id}?sig={sig}&exp={exp}'


def render_handoff_pdf(
    call_id: UUID,
    scenario: ScenarioFixture,
    triage_label: str,
    probe_answers: tuple[str, str, str] | None,
) -> bytes:
    homebrew_library_path = '/opt/homebrew/lib'
    existing_fallback_library_path = os.environ.get('DYLD_FALLBACK_LIBRARY_PATH')
    if existing_fallback_library_path is None:
        os.environ['DYLD_FALLBACK_LIBRARY_PATH'] = homebrew_library_path
    elif homebrew_library_path not in existing_fallback_library_path.split(':'):
        os.environ['DYLD_FALLBACK_LIBRARY_PATH'] = (
            f'{homebrew_library_path}:{existing_fallback_library_path}'
        )

    from weasyprint import HTML

    template = get_pdf_environment().get_template('handoff.html')
    html = template.render(
        call_id=str(call_id),
        generated_at=datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC'),
        patient_name=PATIENT_NAME,
        patient_age=PATIENT_AGE,
        patient_weeks=PATIENT_WEEKS,
        patient_baby=PATIENT_BABY,
        clinician_name=CLINICIAN_NAME,
        triage_label=triage_label,
        flag_time=scenario.flag_at_t,
        rationale=scenario.drivers,
        probe_rows=tuple(zip(PROBE_QUESTIONS, probe_answers or ('Not captured',) * 3)),
        transcript_excerpt=get_transcript_excerpt(scenario),
    )
    return HTML(string=html, base_url=str(TEMPLATE_DIR)).write_pdf()


def store_pdf_artifact(
    registry: PdfRegistry,
    call_id: UUID,
    pdf_bytes: bytes,
) -> PdfArtifact:
    PDF_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    pdf_id = uuid4()
    storage_path = PDF_STORAGE_DIR / f'{pdf_id}.pdf'
    storage_path.write_bytes(pdf_bytes)
    artifact = PdfArtifact(
        id=pdf_id,
        call_id=call_id,
        storage_path=storage_path,
        generated_at=datetime.now(UTC),
    )
    registry.pdfs[pdf_id] = artifact
    return artifact


def get_pdf_artifact(registry: PdfRegistry, pdf_id: UUID) -> PdfArtifact:
    return registry.pdfs[pdf_id]


def update_pdf_sms_dispatch(
    registry: PdfRegistry,
    pdf_id: UUID,
    recipient_phone: str,
    sms_id: str,
    signed_download_url: str,
) -> PdfArtifact:
    artifact = get_pdf_artifact(registry, pdf_id)
    updated_artifact = replace(
        artifact,
        recipient_phone=recipient_phone,
        sms_id=sms_id,
        sms_dispatched_at=datetime.now(UTC),
        signed_download_url=signed_download_url,
    )
    registry.pdfs[pdf_id] = updated_artifact
    return updated_artifact


def update_pdf_sms_delivery(
    registry: PdfRegistry,
    sms_id: str,
    delivered: bool,
) -> PdfArtifact | None:
    for pdf_id, artifact in registry.pdfs.items():
        if artifact.sms_id == sms_id:
            updated_artifact = replace(
                artifact,
                sms_delivered_at=datetime.now(UTC) if delivered else artifact.sms_delivered_at,
            )
            registry.pdfs[pdf_id] = updated_artifact
            return updated_artifact

    return None
