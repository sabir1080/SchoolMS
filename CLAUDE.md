# SchoolMS — working rules

Multi-tenant SaaS school management system (schools, colleges, universities, coaching
and tuition centers). See README.md for stack, structure and API.

## Owner's rules (always follow)

1. The owner works from a mobile phone and does nothing technical. Claude builds,
   deploys and verifies everything.
2. Every change must be **tested and verified** before it is reported:
   - backend: `cd backend && pytest`, and again with `TEST_DATABASE_URL` pointing at a local
     throwaway PostgreSQL. Tests never use `DATABASE_URL` (in cloud sessions that is production Neon),
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
- Academics names come from `src/lib/terms.ts` (`termsFor(tenant)`); never hard-code "Class"/"Section" in UI.
- Use `apps.core.timeutils.tenant_today(tenant)` for "today" (server runs on UTC).
- Aggregations over models with a default `ordering` must call `.order_by()` first (it splits GROUP BY).
- UI accent colour is the `brand-*` palette (from `--brand`, set per institute); never use `indigo-*` directly.
- Chart colours live in `globals.css` (`--series-1`, `--series-2`, `--chart-grid`); validate new ones.
- Gateway hosts are blocked in cloud sessions: payment flows are tested with simulated gateways
  (Playwright `page.route`) and unit tests; never trust a gateway redirect without verification.
- Frontend is a static export (no server code, no dynamic route segments; use query params).

## Deployment (Render + Neon)

- Render services (workspace "My Workspace", region Singapore), auto-deploy from branch `ccr-3b156a9c-h1tcsc`:
  `schoolms-api` (srv-dbg4dul9fdbs73cobqt0) https://schoolms-api-viji.onrender.com and
  `schoolms-web` static site (srv-dbg4e2i9lscs7390imrg) https://schoolms-web-vzpe.onrender.com
- Do not touch other services in the workspace (e.g. `tradeflow_demo`).
- `RENDER_API_KEY` and `DATABASE_URL` (Neon) come from the environment; never print them.
- After pushing, wait for the deploy via the Render API and check the service logs for errors.
- Free plan has no one-off jobs. To run `seed_demo` (rebuilds only the demo institute) on production (only when the owner
  asks): set env var `SEED_DEMO_COMMIT` to the deployed commit SHA, trigger a deploy of that commit,
  check the logs, then DELETE the env var. Demo institute: code `demo`, password `demo1234`.

## Roadmap

Phase 1: setup/roles/login ✅ → institute code login + SaaS subscriptions ✅ → passwords ✅ →
academic setup ✅ → student admission + enrollment ✅ → attendance ✅ → fees & invoices ✅ →
dashboard ✅ → payment gateways JazzCash + Easypaisa ✅ → Safepay + Stripe ✅.

Phase 2: exams + date sheet + grading scale ✅ → marks entry ✅ → per-exam results, position (per
`Tenant.show_position`) & report card print ✅ → combined annual result (weightage set per school) +
parent/student results ✅. Pass rule: `Tenant.pass_percentage` per subject (default 33).

Then (owner asked for all five together): timetable ✅ → homework & diary ✅ → SMS/WhatsApp alerts ✅
(free wa.me links or Twilio) → staff & payroll ✅ → reports with Excel/PDF ✅.

Then: promotion to next class/session ✅ → subject teacher marks entry (timetable teachers) ✅ →
certificates ✅ → white-label logo + theme colour ✅ (`apps.tenants.branding`).

Then: fee receipts + payment message ✅ → online admission form ✅ → student photo + ID cards ✅ →
platform owner dashboard ✅ → PWA + Web Push notifications ✅ → Safepay + Stripe ✅ → backups ✅
(`apps.backups`: download on platform overview, `restore_backup` command). Not yet: library, transport.

- Payments: a gateway payment counts only after server-side verification (signature, read-back or IPN).
- Web Push needs `VAPID_PRIVATE_KEY` on the API service; push endpoints are limited to real push services.
- Stored images (logo, student photo) are small data URLs resized in the browser; validate type and size.

- Menu items carry the plan `feature` they need (`src/lib/navigation.ts`); the layout hides the rest.
- Parent alerts go through `apps.messaging.services.queue_and_send` (dedupe keys, plan check).
