"""Live Firebase Auth smoke — proves a real ID token for this project verifies through the
exact path get_current_uid uses (JWKS fetch + audience + issuer). The main suite overrides
get_current_uid, so this path never runs there.

Provider-agnostic: it mints a custom token with the Admin SDK, exchanges it for a real ID
token via the Identity Toolkit REST API, then verifies it — no browser OAuth needed.
"""

import httpx
from firebase_admin import auth as fb_auth

_EXCHANGE = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken"


def test_id_token_verifies_against_real_project(firebase_live_app, web_api_key, real_project):
    uid = "zzz-live-auth-smoke"
    custom = fb_auth.create_custom_token(uid, app=firebase_live_app).decode()
    resp = httpx.post(
        _EXCHANGE, params={"key": web_api_key},
        json={"token": custom, "returnSecureToken": True}, timeout=20,
    )
    assert resp.status_code == 200, resp.text[:200]
    id_token = resp.json()["idToken"]

    decoded = fb_auth.verify_id_token(id_token, app=firebase_live_app)
    try:
        assert decoded["uid"] == uid
        assert decoded["aud"] == real_project
        assert decoded["iss"] == f"https://securetoken.google.com/{real_project}"
    finally:
        fb_auth.delete_user(uid, app=firebase_live_app)
