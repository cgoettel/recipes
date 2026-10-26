"""The #18 hardening pass: inputs that used to 500, and the auth guards."""

from fractions import Fraction
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from recipes_site import bakers, cf_access, cooklog, counts
from recipes_site.app import create_app
from recipes_site.config import Settings

TEAM = "example"
AUD = "aud-tag"


@pytest.mark.parametrize("value", ["inf", "-inf", "1e999", "nan", "abc"])
def test_dough_scale_ignores_values_without_an_integer(value: str) -> None:
    assert bakers.dough_scale(value, Fraction(1000)) is None


def test_auth_disabled_refused_with_a_full_access_config() -> None:
    with pytest.raises(RuntimeError, match="RECIPES_AUTH_DISABLED"):
        create_app(
            Settings(
                auth_disabled=True,
                cf_access_team_domain=TEAM,
                cf_access_audience=AUD,
                cf_access_allowed_emails="cook@example.com",
            )
        )


def test_auth_disabled_allowed_without_an_audience() -> None:
    # recipes-dev: team domain and allowlist set, audience empty.
    create_app(
        Settings(
            auth_disabled=True,
            cf_access_team_domain=TEAM,
            cf_access_audience="",
            cf_access_allowed_emails="cook@example.com",
        )
    )


@pytest.fixture
def signer(monkeypatch: pytest.MonkeyPatch) -> rsa.RSAPrivateKey:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    fake = SimpleNamespace(
        get_signing_key_from_jwt=lambda _t: SimpleNamespace(key=key.public_key())
    )
    monkeypatch.setattr(cf_access, "_jwks_client", lambda _team: fake)
    return key


def _token(key: rsa.RSAPrivateKey, **claims: str) -> str:
    base = {"aud": AUD, "iss": f"https://{TEAM}.cloudflareaccess.com", "email": "cook@example.com"}
    return jwt.encode(base | claims, key, algorithm="RS256")


def test_verify_accepts_any_email_case(signer: rsa.RSAPrivateKey) -> None:
    token = _token(signer, email="Cook@Example.com")
    allowed = Settings(cf_access_allowed_emails="COOK@example.com").cf_access_allowed_emails_set
    assert cf_access.verify(token, TEAM, AUD, allowed) == "Cook@Example.com"


def test_verify_rejects_another_issuer(signer: rsa.RSAPrivateKey) -> None:
    token = _token(signer, iss="https://other.cloudflareaccess.com")
    with pytest.raises(jwt.InvalidIssuerError):
        cf_access.verify(token, TEAM, AUD, {"cook@example.com"})


def test_cook_log_down_answers_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(counts, "bump", lambda *_a, **_k: None)

    def boom(*_a: object, **_k: object) -> None:
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    monkeypatch.setattr(cooklog, "status", boom)
    monkeypatch.setattr(cooklog, "made_slugs", boom)
    client = TestClient(create_app(Settings(auth_disabled=True)))
    r = client.get("/me/status?slug=breakfast/granola")
    assert r.status_code == 503
    assert r.json() == {"detail": "the cook log is unavailable"}
    page = client.get("/me", headers={"accept": "text/html"})
    assert page.status_code == 503
    assert "can’t be reached" in page.text
