import hashlib
import logging
import secrets
import smtplib
from datetime import datetime
from email.message import EmailMessage

import requests
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.database.models import ApiKey, IntegrationEndpoint, IntegrationTypeEnum

logger = logging.getLogger("integrations")


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def _is_active(flag: int | bool | None) -> bool:
    return bool(flag)


def create_api_key(db: Session, company_id: int, name: str) -> dict:
    raw = f"sk_{secrets.token_urlsafe(32)}"
    prefix = raw[:12]

    key = ApiKey(
        company_id=company_id,
        name=name,
        key_prefix=prefix,
        key_hash=_hash_key(raw),
        is_active=1,
    )
    db.add(key)
    db.commit()
    db.refresh(key)

    return {
        "id": key.id,
        "name": key.name,
        "prefix": key.key_prefix,
        "created_at": key.created_at.isoformat() if key.created_at else None,
        "api_key": raw,
    }


def list_api_keys(db: Session, company_id: int) -> list[dict]:
    rows = (
        db.query(ApiKey)
        .filter(ApiKey.company_id == company_id)
        .order_by(ApiKey.created_at.desc())
        .all()
    )
    return [
        {
            "id": row.id,
            "name": row.name,
            "prefix": row.key_prefix,
            "is_active": _is_active(row.is_active),
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "last_used_at": row.last_used_at.isoformat() if row.last_used_at else None,
        }
        for row in rows
    ]


def revoke_api_key(db: Session, company_id: int, key_id: int) -> bool:
    row = (
        db.query(ApiKey)
        .filter(ApiKey.id == key_id, ApiKey.company_id == company_id)
        .first()
    )
    if not row:
        return False
    row.is_active = 0
    db.commit()
    return True


def resolve_company_from_api_key(db: Session, raw_key: str | None) -> int | None:
    if not raw_key:
        return None
    hashed = _hash_key(raw_key)
    row = (
        db.query(ApiKey)
        .filter(ApiKey.key_hash == hashed, ApiKey.is_active == 1)
        .first()
    )
    if not row:
        return None
    row.last_used_at = datetime.utcnow()
    db.commit()
    return row.company_id


def create_endpoint(
    db: Session,
    company_id: int,
    integration_type: str,
    target: str,
    name: str | None = None,
    secret: str | None = None,
    is_active: bool = True,
) -> IntegrationEndpoint:
    endpoint = IntegrationEndpoint(
        company_id=company_id,
        integration_type=IntegrationTypeEnum(integration_type),
        target=target,
        name=name,
        secret=secret,
        is_active=1 if is_active else 0,
    )
    db.add(endpoint)
    db.commit()
    db.refresh(endpoint)
    return endpoint


def list_endpoints(db: Session, company_id: int) -> list[IntegrationEndpoint]:
    return (
        db.query(IntegrationEndpoint)
        .filter(IntegrationEndpoint.company_id == company_id)
        .order_by(IntegrationEndpoint.created_at.desc())
        .all()
    )


def delete_endpoint(db: Session, company_id: int, endpoint_id: int) -> bool:
    endpoint = (
        db.query(IntegrationEndpoint)
        .filter(IntegrationEndpoint.id == endpoint_id, IntegrationEndpoint.company_id == company_id)
        .first()
    )
    if not endpoint:
        return False
    db.delete(endpoint)
    db.commit()
    return True


def _send_email(recipient: str, subject: str, body: str) -> dict:
    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        logger.info("Skipping email notification: SMTP settings are missing")
        return {"ok": False, "provider": "email", "detail": "smtp_not_configured"}

    message = EmailMessage()
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.INTEGRATION_HTTP_TIMEOUT) as smtp:
            if settings.SMTP_USE_TLS:
                smtp.starttls()
            if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.send_message(message)
        return {"ok": True, "provider": "email"}
    except Exception as exc:
        logger.warning("Email send failed: %s", exc)
        return {"ok": False, "provider": "email", "detail": str(exc)}


def _post_webhook(url: str, payload: dict, secret: str | None = None, provider: str = "webhook") -> dict:
    headers = {"Content-Type": "application/json"}
    if secret:
        headers["X-Webhook-Secret"] = secret

    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=settings.INTEGRATION_HTTP_TIMEOUT,
        )
        return {
            "ok": response.ok,
            "provider": provider,
            "status": response.status_code,
        }
    except Exception as exc:
        logger.warning("Webhook post failed (%s): %s", provider, exc)
        return {"ok": False, "provider": provider, "detail": str(exc)}


def dispatch_event(
    db: Session,
    company_id: int,
    event: str,
    title: str,
    body: str,
    payload: dict,
) -> list[dict]:
    endpoints = list_endpoints(db, company_id)
    active = [ep for ep in endpoints if _is_active(ep.is_active)]
    results: list[dict] = []

    # Optional default org-wide webhooks from env. Some deployments may not
    # define these settings keys, so access them defensively.
    default_slack_webhook = getattr(settings, "DEFAULT_SLACK_WEBHOOK_URL", None)
    default_teams_webhook = getattr(settings, "DEFAULT_TEAMS_WEBHOOK_URL", None)

    if default_slack_webhook:
        results.append(
            _post_webhook(
                default_slack_webhook,
                {"text": f"{title}\n\n{body}"},
                provider="slack-default",
            )
        )
    if default_teams_webhook:
        results.append(
            _post_webhook(
                default_teams_webhook,
                {"text": f"{title}\n\n{body}"},
                provider="teams-default",
            )
        )

    event_payload = {
        "event": event,
        "title": title,
        "body": body,
        "timestamp": datetime.utcnow().isoformat(),
        **payload,
    }

    for endpoint in active:
        endpoint_type = endpoint.integration_type.value
        if endpoint_type == "email":
            results.append(_send_email(endpoint.target, title, body))
        elif endpoint_type == "slack":
            results.append(_post_webhook(endpoint.target, {"text": f"{title}\n\n{body}"}, endpoint.secret, "slack"))
        elif endpoint_type == "teams":
            results.append(_post_webhook(endpoint.target, {"text": f"{title}\n\n{body}"}, endpoint.secret, "teams"))
        else:
            results.append(_post_webhook(endpoint.target, event_payload, endpoint.secret, "webhook"))

    return results
