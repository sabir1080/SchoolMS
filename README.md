# SchoolMS

Multi-tenant SaaS for schools, colleges, universities, coaching and tuition centers.
One web app that works on mobile, laptop and desktop.

## Stack

| Part | Tech |
|---|---|
| Backend | Python, Django 5.2 LTS, Django REST Framework, JWT (simplejwt) |
| Database | PostgreSQL (SQLite locally if `DATABASE_URL` is unset) |
| Frontend | Next.js 15 (React, TypeScript), Tailwind CSS |
| Hosting | Render (`render.yaml` Blueprint) |

## Structure

```
backend/
  config/              Django settings and URLs
  apps/core/           Shared building blocks: TenantScopedModel, role permissions, tenant-scoped viewset mixin
  apps/tenants/        Institutes (tenants), institute code lookup, self-registration, platform API
  apps/accounts/       Users, roles, institute-code login, institute user management
  apps/subscriptions/  SaaS plans, prices, subscriptions, trial, feature gating, plan limits, payments
  tests/
frontend/
  src/lib/             API client, auth context, navigation, regions
  src/components/      Shared UI pieces
  src/app/             Pages: login, register, platform/login, dashboard, users, billing, platform/tenants
render.yaml            Render deployment Blueprint (API web service + free static site)
```

## Login flow

1. `/login/` asks for the **institute code** (e.g. `al-huda`), shows the institute's name.
2. Then username (or email) + password. The code is remembered on the device.
3. Shareable link: `/login/?code=al-huda` skips step 1.
4. Usernames and emails are unique **per institute**.
5. Platform super admin logs in at `/platform/login/` (no code).

## Multi-tenancy

Shared database, every institute-owned row has a `tenant_id`.

- Feature models inherit `apps.core.models.TenantScopedModel`.
- Feature viewsets use `apps.core.mixins.TenantScopedViewSetMixin`, which filters every
  query by `request.user.tenant`, stamps the tenant on create, and enforces the subscription.
- Suspending an institute (`is_active=False`) blocks login and existing tokens for its users.

## SaaS subscriptions

- Plans (seeded: Basic, Pro, Enterprise) with prices per currency and billing cycle, limits
  (`max_students`, `max_staff`, empty = unlimited) and a list of features. Edit them at `/admin/`.
- New institutes get a 14-day trial on Pro (`TRIAL_PLAN_CODE`, `TRIAL_DAYS`).
- When the trial/paid period ends, institute APIs return **402** and the app only shows the billing page.
- Feature viewsets set `required_feature = Feature.X`; plan limits use `check_limit(tenant, "max_students", count)`.
- The super admin records manual payments (bank, JazzCash, Easypaisa, cash...) which extend the
  subscription by 30 or 365 days (from the end of the current period). Online gateways come later.

## Roles

| Role | Tenant | Can do (so far) |
|---|---|---|
| `super_admin` | none | Create, suspend institutes; manage subscriptions and payments |
| `admin` | required | Manage users of their own institute; see plan & billing |
| `teacher`, `student`, `parent` | required | Log in, view dashboard |

## API (so far)

| Method | Path | Who |
|---|---|---|
| GET | `/api/health/` | anyone |
| GET | `/api/public/institutes/<code>/` | anyone (login step 1) |
| GET | `/api/public/plans/` | anyone |
| POST | `/api/public/register/` | anyone (creates institute + admin + trial, returns tokens) |
| POST | `/api/auth/login/` (`institute_code`, `username`, `password`) | anyone |
| POST | `/api/auth/platform-login/` | super admin |
| POST | `/api/auth/refresh/` | anyone with a refresh token |
| GET | `/api/auth/me/` | logged-in user |
| GET | `/api/subscription/` | institute users (works after expiry) |
| GET/POST/PATCH/DELETE | `/api/users/` | institute admin (DELETE deactivates) |
| GET/POST/PATCH | `/api/platform/tenants/` | super admin |
| PATCH | `/api/platform/tenants/<id>/subscription/` | super admin |
| POST | `/api/platform/tenants/<id>/record-payment/` | super admin |
| GET | `/api/platform/tenants/<id>/payments/` | super admin |

Login, lookup and registration are rate-limited.

## Local development

```bash
# Backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r backend/requirements-dev.txt
cd backend && cp .env.example .env
python manage.py migrate
python manage.py ensure_superadmin
python manage.py runserver          # http://localhost:8000
pytest                              # run tests

# Frontend
cd frontend && cp .env.example .env.local
npm install && npm run dev          # http://localhost:3000
```

## Deploying on Render (+ Neon database)

- `schoolms-api`: Python web service (`backend/build.sh` runs migrations and creates the super admin).
- `schoolms-web`: free Static Site built from `frontend/` (`out/`).
- Database: Neon PostgreSQL, connection string in `DATABASE_URL`.

Environment values:

| Service | Key | Value |
|---|---|---|
| api | `DATABASE_URL` | Neon connection string |
| api | `CORS_ALLOWED_ORIGINS` | frontend URL, e.g. `https://schoolms-web.onrender.com` |
| api | `SUPERADMIN_USERNAME` / `_EMAIL` / `_PASSWORD` | platform owner login |
| web | `NEXT_PUBLIC_API_URL` | backend URL, e.g. `https://schoolms-api.onrender.com` |
| web | `NEXT_PUBLIC_SUPPORT_CONTACT` | optional, shown on the billing page |

The free API plan sleeps when idle (first request takes ~30–60 s). Switch it to Starter
before onboarding real institutes.

## Roadmap

Phase 1 (MVP): ~~setup, tenants, roles, login~~ -> ~~institute code login, SaaS subscriptions~~ -> academic setup (session, program, batch)
-> student admission -> enrollment -> attendance -> fees & invoices -> dashboard
-> payment gateways (JazzCash, Easypaisa, Safepay, Stripe).
