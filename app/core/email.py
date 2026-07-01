import os
import smtplib
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTPAuthenticationError, SMTPException

from dotenv import find_dotenv, load_dotenv
from loguru import logger

load_dotenv(find_dotenv(usecwd=True))

PLACEHOLDER_VALUES = {
    "yourgmail@gmail.com",
    "your_app_password",
    "your-app-password",
    "gmail_app_password",
    "your_password",
}


@dataclass
class EmailSendResult:
    sent: bool
    reset_link: str
    error: str | None = None


@dataclass(frozen=True)
class SMTPConfig:
    host: str
    port: int | None
    username: str
    password: str
    from_email: str
    frontend_url: str


class SMTPConfigurationError(RuntimeError):
    pass


def is_production() -> bool:
    return os.getenv("APP_ENV", "development").strip().lower() == "production"


def _env_first(*names: str) -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def get_smtp_config() -> SMTPConfig:
    port_value = _env_first("SMTP_PORT")
    try:
        port = int(port_value) if port_value else None
    except ValueError:
        port = None

    username = _env_first("SMTP_USER", "SMTP_USERNAME")
    from_email = _env_first("SMTP_FROM", "SMTP_FROM_EMAIL")

    return SMTPConfig(
        host=_env_first("SMTP_HOST"),
        port=port,
        username=username,
        password=_env_first("SMTP_PASSWORD"),
        from_email=from_email,
        frontend_url=_env_first("FRONTEND_URL") or "http://localhost:3000",
    )


def validate_smtp_config(config: SMTPConfig | None = None) -> SMTPConfig:
    config = config or get_smtp_config()
    missing = []
    invalid = []

    if not config.host:
        missing.append("SMTP_HOST")
    if config.port is None:
        missing.append("SMTP_PORT")
    if not config.username:
        missing.append("SMTP_USER or SMTP_USERNAME")
    if not config.password:
        missing.append("SMTP_PASSWORD")
    if not config.from_email:
        missing.append("SMTP_FROM or SMTP_FROM_EMAIL")

    for field_name, value in (
        ("SMTP_USER/SMTP_USERNAME", config.username),
        ("SMTP_PASSWORD", config.password),
        ("SMTP_FROM/SMTP_FROM_EMAIL", config.from_email),
    ):
        if value.strip().lower() in PLACEHOLDER_VALUES:
            invalid.append(field_name)

    if missing or invalid:
        sections = []
        if missing:
            sections.append("Missing SMTP variables:\n" + "\n".join(f"- {field}" for field in missing))
        if invalid:
            sections.append(
                "Invalid placeholder SMTP variables:\n" + "\n".join(f"- {field}" for field in invalid)
            )
        error = "\n".join(sections)
        logger.error(error)
        raise SMTPConfigurationError(error)

    return config


def validate_smtp_config_for_startup() -> None:
    try:
        validate_smtp_config()
    except SMTPConfigurationError as exc:
        if is_production():
            raise
        logger.warning(
            "SMTP is not fully configured. APP_ENV=development, so startup will continue. "
            f"Forgot Password will log a local reset URL instead of sending email. Details: {exc}"
        )


async def send_password_reset_email(to_email: str, token: str) -> EmailSendResult:
    fallback_frontend_url = _env_first("FRONTEND_URL") or "http://localhost:3000"
    try:
        config = validate_smtp_config()
    except SMTPConfigurationError as exc:
        reset_link = f"{fallback_frontend_url}/reset-password?token={token}"
        if not is_production():
            logger.warning(f"SMTP unavailable in development mode: {exc}")
            logger.info("RESET PASSWORD URL:")
            logger.info(reset_link)
            return EmailSendResult(sent=True, reset_link=reset_link)
        return EmailSendResult(sent=False, reset_link=reset_link, error=str(exc))

    reset_link = f"{config.frontend_url}/reset-password?token={token}"

    subject = "Reset Your Password"
    body = f"""
    <h2>Password Reset</h2>
    <p>You requested a password reset. Click the link below to reset your password:</p>
    <p><a href="{reset_link}">{reset_link}</a></p>
    <p>This link will expire in 15 minutes.</p>
    <p>If you did not request this, please ignore this email.</p>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config.from_email
    msg["To"] = to_email

    msg.attach(MIMEText(body, "html"))

    try:
        # Run synchronous SMTP in a thread (or just execute it if traffic is low,
        # but using asyncio.to_thread is better in FastAPI)
        import asyncio

        def _send() -> None:
            logger.info(
                f"SMTP connection started: host={config.host}, port={config.port}, user={config.username}"
            )
            with smtplib.SMTP(config.host, config.port or 0, timeout=30) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(config.username, config.password)
                server.send_message(msg)

        await asyncio.to_thread(_send)
        logger.info(f"Email sent successfully to {to_email}")
        return EmailSendResult(sent=True, reset_link=reset_link)
    except SMTPAuthenticationError as e:
        error = f"SMTP authentication failed: {e.smtp_code} {e.smtp_error!r}"
        logger.exception(error)
        return EmailSendResult(sent=False, reset_link=reset_link, error=error)
    except OSError as e:
        error = f"SMTP connection failed: {type(e).__name__}: {e}"
        logger.exception(error)
        return EmailSendResult(sent=False, reset_link=reset_link, error=error)
    except SMTPException as e:
        error = f"SMTP error: {type(e).__name__}: {e}"
        logger.exception(error)
        return EmailSendResult(sent=False, reset_link=reset_link, error=error)
    except (RuntimeError, ValueError) as e:
        error = f"{type(e).__name__}: {e}"
        logger.exception(f"Full email sending error details for {to_email}: {error}")
        return EmailSendResult(sent=False, reset_link=reset_link, error=error)
