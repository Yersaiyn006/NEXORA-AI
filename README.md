# NEXORA AI — Engineering audit update

Existing Django SaaS prototype: operator invitations → business owner setup → catalog and knowledge → company-specific Gemini consultant → customer requests and CRM.

## Quick update on Windows

1. Stop `runserver`. Back up the existing project and `db.sqlite3`; keep your existing `.env`.
2. Copy the archive contents into the existing project root (where `manage.py` lives). Do not replace the database or `.env`: neither is included.
3. Use **Python 3.12+** for Django 6.0.9. A copied `.venv` from another computer must be recreated.
4. In the activated environment:

```powershell
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py check
python manage.py test
python manage.py runserver
```

New migrations are included: do not generate your own with `makemigrations` when installing this update.

5. Sign in at `/accounts/login/`; Django admin remains the operator's tool.
6. Test the full workflow using a private browser window for customers, then verify `/studio/?tab=requests`.
7. Run `python manage.py purge_rate_limits` daily to remove expired counters.

## Configuration

`.env.example` documents the options. Keep `GEMINI_API_KEY` and `DJANGO_SECRET_KEY` in `.env`, which stays out of source control. The existing `.env` loading mechanism is preserved. Gemini defaults to `gemini-2.5-flash`, exactly as in the input archive; set `NEXORA_AI_MODEL` explicitly if your account uses a different supported model.

`NEXORA_AI_ENABLED=true` keeps Gemini as the primary engine. Local factual fallbacks are used only when it is unavailable. Tests use mocks and synthetic data; production keys are not required for `manage.py test`.

## Verification and scope

Read `docs/TEST_RESULTS.md`, `docs/BUG_SECURITY_REPORT.md`, and `docs/EXECUTIVE_SUMMARY.md`. Mock tests validate integration wiring, context selection, authorization and state changes; they do **not** prove live Gemini factual quality or injection resistance. No real client database was supplied or changed.

Production deployment needs a separately tested PostgreSQL setup, HTTPS, backup restore drills, a production WSGI/ASGI server, static asset hosting, trusted proxy configuration, monitoring, per-tenant budgets and verified notification/handoff behavior. `NEXORA_PRODUCTION=true` enables basic HTTPS cookies/redirect/HSTS, but is not a production certification.

## Source layout

- `core`: tenancy, operator invitation/onboarding, authentication, dashboard, distribution.
- `business_brain`: structured company profile and catalog.
- `assistant_ai`: knowledge, dialogue, Gemini context/transport, turn serialization, request collection, limits.
- `public_chat`: session-owned anonymous chat.
- `business_center`: owner workspace, knowledge editor, CRM and scheduling.

Channels such as Telegram/WhatsApp/Instagram are model choices in this archive, not implemented integrations.

## Revalidation update — 9 October 2026

Run the included migration 0005 after the earlier additive migrations. Request actions and recovery receipts commit together, so retrying a failed reply save does not corrupt request collection. `NEXORA_AI_BUSINESS_PER_DAY` and `NEXORA_AI_GLOBAL_PER_DAY` bound Gemini attempts across public chat and Playground. Defaults are 1000/5000 attempts, not a currency budget; adjust before a pilot. See `docs/REVERIFY.md` for current evidence and remaining limitations.
