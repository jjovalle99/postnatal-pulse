from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from twilio.request_validator import RequestValidator

from postnatal_pulse.main import app
from postnatal_pulse.config import get_settings


def create_twilio_signature() -> str:
    validator = RequestValidator(get_settings().twilio_auth_token)
    return validator.compute_signature(
        'http://testserver/twilio/voice',
        {
            'CallSid': 'CA123',
            'From': '+441234567890',
            'To': '+449876543210',
        },
    )


async def test_twilio_voice_rejects_invalid_signature() -> None:
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url='http://testserver',
        ) as client:
            response = await client.post(
                '/twilio/voice',
                headers={'X-Twilio-Signature': 'invalid'},
                data={
                    'CallSid': 'CA123',
                    'From': '+441234567890',
                    'To': '+449876543210',
                },
            )

    assert response.status_code == 403


async def test_twilio_voice_returns_stream_twiml() -> None:
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url='http://testserver',
        ) as client:
            response = await client.post(
                '/twilio/voice',
                headers={'X-Twilio-Signature': create_twilio_signature()},
                data={
                    'CallSid': 'CA123',
                    'From': '+441234567890',
                    'To': '+449876543210',
                },
            )

    assert response.status_code == 200
    assert response.headers['content-type'].startswith('text/xml')
    assert '<Stream url="ws://testserver/ws/twilio/media"' in response.text
