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
  apps/academics/      Sessions, programs (class/course), sections (section/batch), subjects
  apps/students/       Students, guardians (shared by siblings), enrollments, student/parent portals
  apps/attendance/     Daily attendance per section, monthly reports, today summary
  apps/fees/           Fee types, class fees per session, discounts, invoices, payments, summary
  apps/dashboard/      One endpoint with the admin/teacher dashboard numbers and trends
  apps/payments/       Online fee payments: JazzCash, Easypaisa and a demo gateway
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

## Passwords

- Each institute picks a password policy in Institute settings: **easy** (default, 4+ characters),
  **standard** (8+, not a common password) or **strong** (8+, letters and numbers, not common).
- Super admins follow `PLATFORM_PASSWORD_POLICY` (default `standard`).
- Users change their own password; admins reset their users' passwords; the super admin can reset an
  institute admin's password. Email "forgot password" comes with the alerts module (Phase 2).

## Academic setup

- **Session**: academic year/term (one is "current"; the first one added becomes current).
- **Program**: class, grade, course or degree program. **Section**: section, batch or group of a
  program in one session, with an optional class teacher and capacity. **Subject**: linked to programs.
- Names follow the institute type (school: Class/Section, coaching: Course/Batch, university:
  Program/Section, tuition: Class/Batch) and can be renamed in Institute settings.
- Admins edit (bulk "one per line" add for programs and subjects); teachers can read. Items in use
  cannot be deleted (mark them inactive instead). Requires the `academics` plan feature.

## Students

- Admission form: student details, automatic admission number (1, 2, 3 ... per institute; a manual
  number can be typed), optional class/section + roll number, and guardians.
- A guardian whose phone already exists in the institute is reused, so siblings share one parent.
- Enrollment = a student's section for one session; changing class keeps the history. Roll numbers
  are unique within a section.
- Statuses: active, left, graduated, suspended. Only active students count toward `max_students`,
  and a student's login works only while active.
- Admins can create student and parent logins; parents see their children and students their own
  profile on the dashboard. Teachers can view students; only admins can change them.

## Attendance

- Daily, per section: Present, Absent, Leave or Late (one record per student per day). Re-saving
  a date updates it. No future dates; the date must be inside the section's session.
- Admins can take attendance for every section; teachers only for sections where they are the
  class teacher. "Today" uses the institute's timezone.
- Percentage = (Present + Late) / (days taken − Leave days); leave does not lower it. Monthly report per section with a day-by-day grid.
- Dashboard: today's summary and sections not yet marked (admin/teacher); parents and students see
  today's status and monthly/session percentages. Students with attendance cannot be deleted.

## Fees

- Fee types are monthly or once per session (e.g. admission). Each class gets an amount per fee
  type for a session; 0 removes a fee.
- Student discounts (fixed amount or percent) per fee type, applied when bills are made.
- "Create bills" makes one invoice per active student for a month: monthly fees plus once-per-session
  fees not billed yet. Re-running skips students who already have that month's bill. One-off bills
  (trip, books, fine) can be created for a single student.
- Payments can be partial; amounts above the balance are refused. Invoice and receipt numbers count
  up per institute. Bills with payments cannot be cancelled until the payments are deleted.
- Overview: billed and received this month, total due, overdue students. Bills print cleanly.
- Admins only. Parents and students see their bills. Students with bills cannot be deleted.

## Dashboard

- Admin: active students (new this month), attendance today and sections marked, fees received this
  month and total due (overdue students), students not in any section, attendance for the last 14
  school days, fees billed vs received for 6 months, students per class, low attendance (< 75%).
- Teacher: the same for their own sections, without fees. Parents and students keep their cards.
- Charts are plain HTML (no chart library), with a hover/focus readout and a "Show as table" view;
  colours are validated for colour-blind separation in light and dark mode.

## Online payments

- Each institute adds its own merchant accounts in Institute settings (plan feature
  `online_payments`): JazzCash (Merchant ID, Password, Integrity Salt) and Easypaisa (Store ID,
  16-character Hash Key). Secrets are write-only. "Test mode" uses the gateways' sandbox systems.
- Parents/students (and admins) see "Pay with JazzCash / Easypaisa" on open bills. The browser posts
  a signed form to the gateway (hosted checkout) and comes back to `/pay/result/`.
- JazzCash: `pp_SecureHash` = HMAC-SHA256 (integrity salt) over the salt and sorted non-empty `pp_*`
  values; the reply is verified (hash, merchant, amount, response code `000`) before the payment is
  recorded.
- Easypaisa: `merchantHashedReq` = AES-128-ECB/PKCS5 (hash key), base64; the `auth_token` is confirmed
  via `Confirm.jsf`; the final redirect alone is not trusted — the payment is recorded when the
  IPN (`/api/pay/easypaisa/ipn/`, set in the Easypaisa portal) reports it PAID with the right amount.
- Demo gateway (admins only) to try the flow without a merchant account.
- `FRONTEND_URL` (defaults to the first CORS origin) is where customers are sent back to.

## Exams (Phase 2)

- Plan feature `exams`. Many exams per session (monthly tests, first term, mid-term, final), each
  for chosen classes. Status: being prepared (`draft`) -> marks entry open -> result published.
- Creating an exam adds a paper for every active subject of each class (100 marks; pass marks from
  the institute's pass percentage, default 33%). Admins edit marks, date and time per paper, remove
  or add subjects, and print the date sheet per class.
- Grading scale per institute (default A+ 90, A 80, B 70, C 60, D 50, E 33, F 0); the lowest grade
  must start at 0%. Institute settings `pass_percentage` and `show_position` (position on report cards).
- Teachers see exams and grading read-only. Parents and students see the date sheets of announced
  (non-draft) exams of the current session on their dashboard.
- Marks entry (only while the exam is "marks entry open"): admins for every section, teachers for
  sections they are class teacher of. Per section and subject: marks (halves allowed, up to the
  paper's total) or Absent; empty means not entered yet. The exam page shows progress per section.
- Once a subject has marks it cannot be removed, its total cannot go below the highest mark, and
  the exam/class cannot be deleted. Publishing the result locks the marks.
- Results per section: total, percentage, grade and remark (grading scale), pass/fail (a student
  fails if any subject is below its pass marks or absent; missing marks = "Incomplete"), and position
  (1, 2, 2, 4 among students who passed; hidden when `show_position` is off). Summary: pass rate,
  average, highest. Printable result sheet (landscape) and report cards (one A4 page per student,
  with attendance up to the exam's last day). Admins see all sections, class teachers their own.
- Annual (combined) result: an admin picks exams of a session and their weights (adding up to 100%,
  e.g. First Term 25% + Mid-Term 25% + Final 50%). Annual % = weighted exam percentages; each subject's
  weighted % must reach the pass percentage. If a class does not take one of the exams, the others are
  scaled up to 100%. Result sheet and annual report cards like the exam result.
- Parents and students see published exam results and published annual results of the current
  session on their dashboard ("Results") and can open, print or save the report card as PDF.

## Demo institute

`python manage.py seed_demo` creates "Bright Future Academy" (institute code `demo`, password `demo1234`
for users `admin`, `sana` (teacher), `rashid` (parent of two), `ahmed` (student)) with 32 students,
attendance since September, six months of fees, four exams (First Term published with marks) and an
annual result being prepared. Running it again replaces
the demo. `--wipe-all` first deletes **every** institute and its data (super admins and plans stay).

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
| POST | `/api/auth/change-password/` (`current_password`, `new_password`) | any logged-in user |
| GET | `/api/subscription/` | institute users (works after expiry) |
| GET/PATCH | `/api/institute/settings/` | institute admin (details, password policy, labels) |
| CRUD | `/api/academics/sessions/`, `programs/`, `sections/`, `subjects/` | admin (teachers read) |
| POST | `/api/academics/programs/bulk-create/`, `subjects/bulk-create/` (`names`) | institute admin |
| POST | `/api/academics/programs/reorder/` (`ids` in display order) | institute admin |
| CRUD | `/api/students/` (`?search=`, `program`, `section`, `session`, `status`, `unassigned=1`) | admin (teachers read) |
| POST | `/api/students/<id>/enroll/`, `create-login/`; DELETE `.../enrollments/<id>/` | institute admin |
| GET/PATCH | `/api/guardians/` (`?phone=`), POST `/api/guardians/<id>/create-login/` | admin (teachers read) |
| GET | `/api/me/children/` (parent), `/api/me/student/` (student) | parent / student |
| GET | `/api/attendance/sections/`, `today/` | admin / teacher |
| GET/POST | `/api/attendance/sheet/` (`?section=&date=`; POST `section`, `date`, `records`) | admin / class teacher |
| GET | `/api/attendance/report/?section=&month=YYYY-MM`, `/api/attendance/students/<id>/` | admin / teacher |
| GET | `/api/me/attendance/` (`?student=` for parents) | parent / student |
| CRUD | `/api/fees/heads/` (+ `bulk-create/`), `/api/fees/discounts/` (`?student=`) | institute admin |
| GET/POST | `/api/fees/rates/` (`?session=`; POST `session`, `program`, `rates`) | institute admin |
| GET/POST | `/api/fees/invoices/` (`?status=due|overdue|paid|…`, `period`, `program`, `section`, `student`, `search`) | institute admin |
| POST | `/api/fees/invoices/generate/`, `<id>/payments/`, `<id>/cancel/`; DELETE `/api/fees/payments/<id>/` | institute admin |
| GET | `/api/fees/summary/?month=YYYY-MM` | institute admin |
| GET | `/api/me/invoices/` (`?student=` for parents) | parent / student |
| GET | `/api/dashboard/` | admin / teacher |
| CRUD | `/api/exams/` (`?session=`, default current session) | admin; teachers read |
| GET/PUT | `/api/exams/<id>/papers/` (`?program=`; PUT `program`, `papers`, `remove`, `add`) | admin; teachers read |
| GET | `/api/exams/<id>/datesheet/?program=` | admin / teacher |
| GET/PUT | `/api/exams/grading/` (PUT `bands`) | admin; teachers read |
| GET/PUT | `/api/exams/<id>/marks/` (`?section=&paper=`; PUT `section`, `paper`, `entries`) | admin / class teacher |
| GET | `/api/exams/<id>/marks/progress/` | admin / class teacher |
| GET | `/api/exams/<id>/results/?section=` (`&attendance=1` adds attendance) | admin / class teacher |
| CRUD | `/api/combined-results/` (`?session=`; `components`: `[{exam, weight}]`) | admin; teachers read |
| GET | `/api/combined-results/<id>/results/` (sections; `?section=` for the result) | admin / class teacher |
| GET | `/api/me/results/` (`?student=` for parents) | parent / student |
| GET | `/api/me/exams/` (`?student=` for parents) | parent / student |
| GET/PATCH | `/api/pay/settings/` | institute admin |
| GET | `/api/pay/options/`, `/api/pay/status/?ref=`; POST `/api/pay/start/` (`invoice`, `provider`) | admin / parent / student |
| GET | `/api/pay/attempts/?invoice=`; POST `/api/pay/demo/complete/` | institute admin |
| POST/GET | `/api/pay/jazzcash/return/`, `/api/pay/easypaisa/postback/`, `/api/pay/easypaisa/ipn/` | gateways (public) |
| POST | `/api/users/<id>/set-password/` | institute admin |
| GET/POST/PATCH/DELETE | `/api/users/` | institute admin (DELETE deactivates) |
| GET/POST/PATCH | `/api/platform/tenants/` | super admin |
| PATCH | `/api/platform/tenants/<id>/subscription/` | super admin |
| POST | `/api/platform/tenants/<id>/record-payment/` | super admin |
| GET | `/api/platform/tenants/<id>/payments/` | super admin |
| POST | `/api/platform/tenants/<id>/reset-admin-password/` | super admin |

Login, lookup and registration are rate-limited (login: per account and IP, plus a looser per-IP cap so a
school computer lab can log in together). List endpoints accept `?page_size=` (max 500).

## Local development

```bash
# Backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r backend/requirements-dev.txt
cd backend && cp .env.example .env
python manage.py migrate
python manage.py ensure_superadmin
python manage.py runserver          # http://localhost:8000
pytest                              # run tests (SQLite; never uses DATABASE_URL)
TEST_DATABASE_URL=postgres://... pytest   # run tests on a throwaway PostgreSQL

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

Phase 1 (MVP): ~~setup, tenants, roles, login~~ -> ~~institute code login, SaaS subscriptions~~ -> ~~passwords~~ -> ~~academic setup~~ -> ~~student admission & enrollment~~
-> ~~attendance~~ -> ~~fees & invoices~~ -> ~~dashboard~~
-> ~~payment gateways (JazzCash, Easypaisa)~~ -> later: Safepay, Stripe.

Phase 2: ~~exams, date sheet, grading scale~~ -> ~~marks entry~~ -> ~~results, position & report cards~~
-> ~~combined (weighted) annual result and parent/student results~~.
