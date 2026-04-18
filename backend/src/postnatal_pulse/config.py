from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = BACKEND_DIR.parent
DEFAULT_TWILIO_ACCOUNT_SID = "AC00000000000000000000000000000000"
DEFAULT_TWILIO_AUTH_TOKEN = "test-twilio-auth-token"
DEFAULT_TWILIO_PHONE_NUMBER = "+10000000000"


class AppSettings(BaseSettings):
    api_key: str = Field(default="dev-api-key", alias="API_KEY")
    cors_allowed_origins_raw: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173,https://postnatal-pulse.vercel.app",
        alias="CORS_ALLOWED_ORIGINS",
    )
    speechmatics_api_key: str = Field(
        default="test-speechmatics-key",
        alias="SPEECHMATICS_API_KEY",
    )
    speechmatics_rt_url: str | None = Field(
        default=None,
        alias="SPEECHMATICS_RT_URL",
    )
    thymia_api_key: str = Field(default="test-thymia-key", alias="THYMIA_API_KEY")
    thymia_server_url: str = Field(
        default="wss://ws.thymia.ai",
        alias="THYMIA_SERVER_URL",
    )
    live_provider_enabled: bool = Field(
        default=False,
        alias="LIVE_PROVIDER_ENABLED",
    )
    twilio_account_sid: str = Field(
        default=DEFAULT_TWILIO_ACCOUNT_SID,
        alias="TWILIO_ACCOUNT_SID",
    )
    jwt_secret: str = Field(
        default="dev-jwt-secret-with-32-plus-characters",
        alias="JWT_SECRET",
    )
    pdf_signing_secret: str = Field(
        default="dev-pdf-signing-secret",
        alias="PDF_SIGNING_SECRET",
    )
    twilio_auth_token: str = Field(
        default=DEFAULT_TWILIO_AUTH_TOKEN,
        alias="TWILIO_AUTH_TOKEN",
    )
    twilio_phone_number: str = Field(
        default=DEFAULT_TWILIO_PHONE_NUMBER,
        alias="TWILIO_PHONE_NUMBER",
    )

    model_config = SettingsConfigDict(
        env_file=(ROOT_DIR / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @field_validator("api_key", mode="before")
    @classmethod
    def default_blank_api_key(cls, value: object) -> object:
        if value == "":
            return "dev-api-key"

        return value

    @field_validator("pdf_signing_secret", mode="before")
    @classmethod
    def default_blank_pdf_signing_secret(cls, value: object) -> object:
        if value == "":
            return "dev-pdf-signing-secret"

        return value

    @field_validator("twilio_auth_token", mode="before")
    @classmethod
    def default_blank_twilio_auth_token(cls, value: object) -> object:
        if value == "":
            return DEFAULT_TWILIO_AUTH_TOKEN

        return value

    @field_validator("twilio_account_sid", mode="before")
    @classmethod
    def default_blank_twilio_account_sid(cls, value: object) -> object:
        if value == "":
            return DEFAULT_TWILIO_ACCOUNT_SID

        return value

    @field_validator("twilio_phone_number", mode="before")
    @classmethod
    def default_blank_twilio_phone_number(cls, value: object) -> object:
        if value == "":
            return DEFAULT_TWILIO_PHONE_NUMBER

        return value

    @field_validator("thymia_api_key", mode="before")
    @classmethod
    def default_blank_thymia_api_key(cls, value: object) -> object:
        if value == "":
            return "test-thymia-key"

        return value

    @field_validator("thymia_server_url", mode="before")
    @classmethod
    def default_blank_thymia_server_url(cls, value: object) -> object:
        if value == "":
            return "wss://ws.thymia.ai"

        return value

    @field_validator("speechmatics_api_key", mode="before")
    @classmethod
    def default_blank_speechmatics_api_key(cls, value: object) -> object:
        if value == "":
            return "test-speechmatics-key"

        return value

    @field_validator("jwt_secret", mode="before")
    @classmethod
    def default_blank_jwt_secret(cls, value: object) -> object:
        if value == "":
            return "dev-jwt-secret-with-32-plus-characters"

        return value

    @field_validator("cors_allowed_origins_raw", mode="before")
    @classmethod
    def default_blank_cors_allowed_origins(cls, value: object) -> object:
        if value == "":
            return "http://localhost:5173,http://127.0.0.1:5173,https://postnatal-pulse.vercel.app"

        return value

    @property
    def cors_allowed_origins(self) -> tuple[str, ...]:
        return tuple(
            origin.strip()
            for origin in self.cors_allowed_origins_raw.split(",")
            if origin.strip() != ""
        )


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return AppSettings()
