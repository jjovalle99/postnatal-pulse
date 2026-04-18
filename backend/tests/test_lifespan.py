from asgi_lifespan import LifespanManager

from postnatal_pulse.main import app


async def test_app_boots() -> None:
    async with LifespanManager(app):
        pass
