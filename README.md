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
  config/            Django settings and URLs
  apps/core/         Shared building blocks: TenantScopedModel, role permissions, tenant-scoped viewset mixin
  apps/tenants/      Institutes (tenants) + platform API for the super admin
  apps/accounts/     Users, roles, JWT login, institute user management
  tests/
frontend/
  src/lib/           API client, auth context, role-based navigation
  src/components/    Shared UI pieces
  src/app/           Pages (login, dashboard, users, platform/tenants)
render.yaml          Render deployment Blueprint
```

## Multi-tenancy

Shared database, every institute-owned row has a `tenant_id`.

- Feature models inherit `apps.core.models.TenantScopedModel`.
- Feature viewsets use `apps.core.mixins.TenantScopedViewSetMixin`, which filters every
  query by `request.user.tenant` and stamps the tenant on create.
- Suspending an institute (`is_active=False`) blocks login and existing tokens for its users.

## Roles

| Role | Tenant | Can do (so far) |
|---|---|---|
| `super_admin` | none | Create, list, suspend institutes (`/api/platform/tenants/`) |
| `admin` | required | Manage users of their own institute (`/api/users/`) |
| `teacher`, `student`, `parent` | required | Log in, view dashboard |

## API (so far)

| Method | Path | Who |
|---|---|---|
| GET | `/api/health/` | anyone |
| POST | `/api/auth/login/` (username or email + password) | anyone |
| POST | `/api/auth/refresh/` | anyone with a refresh token |
| GET | `/api/auth/me/` | logged-in user |
| GET/POST/PATCH/DELETE | `/api/users/` | institute admin (DELETE deactivates) |
| GET/POST/PATCH | `/api/platform/tenants/` | super admin (POST also creates the first admin) |

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

## Deploying on Render

1. Render dashboard -> **New** -> **Blueprint** -> select this repository.
2. Fill in the values Render asks for:
   - `SUPERADMIN_USERNAME`, `SUPERADMIN_EMAIL`, `SUPERADMIN_PASSWORD`: your platform owner login.
   - `CORS_ALLOWED_ORIGINS`: the frontend URL, e.g. `https://schoolms-web.onrender.com`.
   - `NEXT_PUBLIC_API_URL`: the backend URL, e.g. `https://schoolms-api.onrender.com`.
3. Deploy. Migrations and super admin creation run automatically in `backend/build.sh`.

If a URL changes, update the env var and redeploy (the frontend needs a rebuild for
`NEXT_PUBLIC_API_URL`).

The free plans are for testing only: free web services sleep when idle and the free
database is deleted after 30 days. Upgrade before onboarding real institutes.

## Roadmap

Phase 1 (MVP): ~~setup, tenants, roles, login~~ -> academic setup (session, program, batch)
-> student admission -> enrollment -> attendance -> fees & invoices -> dashboard
-> subscription plans -> payment gateways (JazzCash, Easypaisa, Safepay, Stripe).
