# SchoolMS — working rules

Multi-tenant SaaS school management system (schools, colleges, universities, coaching
and tuition centers). See README.md for stack, structure and API.

## Owner's rules (always follow)

1. The owner works from a mobile phone and does nothing technical. Claude builds,
   deploys and verifies everything.
2. Every change must be **tested and verified** before it is reported:
   - backend: `cd backend && pytest` (also against PostgreSQL),
   - frontend: `npm run lint`, `npx tsc --noEmit`, `npm run build`,
   - a real browser run (Playwright) of the changed flows on mobile and desktop sizes.
3. Find and fix errors and bugs before reporting. Never hand over half-working code.
4. After each step send a report in Roman Urdu: what was built, what was tested,
   any known limitations, and **how the owner can run and check it** (URLs, logins,
   steps to click).
5. Work one feature at a time, in the phase order below, and confirm before the next one.

## Architecture conventions

- Every institute-owned model inherits `apps.core.models.TenantScopedModel`.
- Every institute API viewset uses `apps.core.mixins.TenantScopedViewSetMixin` and sets
  `required_feature` (from `apps.subscriptions.features.Feature`) so plan gating applies.
- Plan limits are checked with `apps.subscriptions.gating.check_limit`.
- Users log in with institute code + username/password. Usernames and emails are unique
  per institute. Super admins log in at `/platform/login` (no institute).
- Frontend is a static export (no server code, no dynamic route segments; use query params).

## Roadmap

Phase 1: setup/roles/login ✅ → institute code login + SaaS subscriptions ✅ →
academic setup → student admission → enrollment → attendance → fees & invoices →
dashboard → payment gateways (JazzCash, Easypaisa, Safepay, Stripe).
