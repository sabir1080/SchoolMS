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
- Safepay (API key + Secret key, PKR): a tracker is created (`/order/v1/init`) and the browser goes to
  Safepay's checkout; the return is accepted only for our tracker with `sig` = HMAC-SHA256(secret, tracker).
- Stripe (Secret key `sk_...`, optional webhook secret `whsec_...`, the institute's currency): a Checkout
  Session is created; the payment counts only after the session is read back from Stripe (on return) or a
  `checkout.session.completed` webhook (`/api/pay/stripe/webhook/<code>/`) with a valid `Stripe-Signature`
  arrives; amount and currency are checked. Test or live follows the key.
- Every recorded payment has a printable receipt (`/receipt/?id=`) and sends parents a thank-you message.
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
- Marks entry (only while the exam is "marks entry open"): admins for every section, class teachers
  for every subject of their section, and subject teachers (from the timetable) for the subjects they
  teach in a section. Per section and subject: marks (halves allowed, up to the
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

## Timetable

- Plan feature `timetable`. Bell schedule (periods and breaks; quick setup makes the whole day) and
  school days (`Tenant.working_days`, Monday–Friday by default).
- Class timetable: subject, teacher and room per period; a teacher cannot be in two classes at the
  same time. Teacher timetable (teachers see their own). Parents/students: today's classes + full week.

## Homework & diary

- Plan feature `homework`. Teachers write the diary for sections they are class teacher of or teach in
  the timetable; admins for all. Only the writer or an admin edits. Parents/students see the last two
  weeks and anything still due.

## Messages to parents (SMS / WhatsApp)

- Plan feature `sms_alerts`. Outbox of messages to the student's primary guardian (Pakistani numbers
  normalised to +92): absent alerts (same day; withdrawn if the child is marked present while still
  waiting), results when an exam is published, homework (optional), fee reminders (once a day, on
  request) and notices (all parents or one section).
- Channels: free "WhatsApp link" (each message opens wa.me with the text; marked sent when opened) or
  Twilio SMS / WhatsApp (sent automatically; failures stay in the outbox to retry). The Twilio token
  is write-only.

## Staff & payroll

- Plan feature `payroll`. Staff records (teachers linked to their login, and other staff) with basic
  salary and allowance. Monthly salary slips made in one tap (salary copied at that time), bonus and
  deductions, mark paid (cash/bank/JazzCash/Easypaisa) or undo, printable slip. Teachers see their own.

## Online admission form

- Plan feature `admissions` (all plans). Institute settings `admissions_open`; admins open/close it on the
  Admissions page and share the link `/apply/?code=<institute code>` (also shown on the login page).
- Parents fill student and guardian details (honeypot field, 20 forms/hour per IP). Admins admit (creates
  the student, guardian and enrollment, sends a welcome message) or decline with a reason.

## Student photos and ID cards

- Student photo (shrunk to 300 px in the browser, stored as a small data URL). ID cards at card size
  (85.6 × 54 mm), front and back, with logo, photo, details and a QR code; one student or a whole section.

## Phone app (PWA) and notifications

- Manifest, icons and a service worker (`public/sw.js`): installable ("Install app on this phone"),
  offline page, and opening offline keeps the login.
- Web Push (`apps/messaging/push.py`, no extra libraries): every parent alert queued through
  `queue_and_send` is also sent as a notification to the parents' and student's devices. Needs
  `VAPID_PRIVATE_KEY` (`python manage.py generate_vapid_keys`); only real push services are contacted.

## Platform owner dashboard

- `/platform/overview` (super admin landing page): institutes by status, plans, students, users,
  subscription revenue per month, renewals due in 14 days, expired institutes, newest institutes and payments.

## About, user manual and owner guide

- `/about`: public product page. `/manual`: step-by-step user manual (English / Roman Urdu, filter by role,
  search, screenshots from the demo in `public/manual/`, refreshed with `node scripts/shoot-manual.js`), content in
  `frontend/src/lib/manual.ts` (keep button names in sync with the app). Linked under every
  login card and as "Help & manual" in the menu.
- `/platform/guide`: the platform owner's guide (Roman Urdu) with live plans and a developer appendix.

## Subscription agreements

- Registration requires accepting the free trial agreement (`accept_terms`); institutes created by the owner accept it on
  Plan & Billing. Paid plans: the admin signs a subscription agreement (details, typed-name e-signature) before paying;
  it waits as "payment pending" with the owner's payment instructions; recording the payment (`record-payment`,
  optional `agreement`) activates it with the paid period. Each agreement stores the exact text, provider details,
  version, signer, time and IP (`apps.agreements`); the owner edits business details at `/platform/business`.

## Backups

- Platform overview → "Download backup" (super admin): one `.json.gz` with every institute's data
  (`dumpdata` without content types, permissions, sessions and logs; plain ids, because usernames repeat
  across institutes). The card turns red when the last download is 7+ days old. The file holds password
  hashes and gateway keys: keep it private.
- Restore into an empty, migrated database: `python manage.py restore_backup <file>` (refuses a database
  that already has institutes). `python manage.py create_backup <file>` makes one from the command line.
- Per institute (`apps.backups.institute`): the institute admin downloads its own file (gateway keys and Twilio
  token blanked) and an Excel workbook from Institute settings → Data backup (also on Plan & Billing when expired).
  The owner downloads one institute (with keys) and restores ONLY that institute from its file or from a full
  backup: preview first, then the institute code to confirm. The current data is saved as an `InstituteSnapshot`
  (last 5 kept) so a restore can be undone. Subscription, payments, agreements and push devices are not touched;
  blank secrets keep their current values. Rows outside the backup that point at the institute's users (push
  devices, agreement signers, "deleted by", "created by") are saved and re-linked.
- Institute admins can restore too, but only a file SchoolMS made for their institute, unchanged: every institute
  file carries an HMAC signature (`salted_hmac` over the rows, tied to the tenant id). A full backup, an edited file
  or a backup without the admin's own login is refused; admins can list and put back saved copies but not download
  them (they hold payment keys).

## Recycle bin

- Deletes in institute modules go through `apps.recyclebin.services.trash()` (or `RecycleBinMixin`): the object and
  everything it cascades to is stored in `DeletedItem` for 30 days (`KEEP_DAYS`). Admins restore it at `/recycle-bin`
  with the same IDs; SET_NULL links are re-linked and invoice totals refreshed. A clash (same number reused) gives a
  clear error instead of a partial restore.

## Promotion to the next class / session

- Students page -> "Promote to next class": pick a section of the current session and the new session.
  Each student gets a suggestion from the latest published annual (or exam) result: passed -> next
  class, failed -> repeat. Per student: promote, repeat, left, graduated (last class) or skip.
  Sections with the same name are created in the new session; roll numbers are kept when free.
  Students marked left/graduated lose portal access with their parents (if no other child studies).

## Certificates

- Plan feature `certificates` (all plans). Character, school leaving and bonafide certificates per
  student, numbered `CERT-0001` per institute, printable on one A4 page with the logo. A leaving
  certificate can mark the student as left. Details are saved with the certificate, so reprints match.

## White-label (logo and theme colour)

- Plan feature `white_label` (Pro, Enterprise). Institute settings -> "Logo and theme colour": upload
  a PNG/JPG/WebP logo (shrunk to 256 px in the browser, saved as a small data URL, max ~150 KB) and
  pick one of 8 theme colours (all readable with white text). Shown on the login page (after the code),
  menu, report cards, certificates and salary slips. Without the feature the defaults are shown and
  changes are refused. Frontend colours use the `brand-*` Tailwind palette derived from `--brand`.

## Reports

- Plan feature `reports` (plus each report's module): student list, monthly attendance, fee dues,
  fee collection, exam result sheet, salaries. Preview, Excel download (openpyxl) or print to PDF.

## Demo institute

`python manage.py seed_demo` creates "Bright Future Academy" (institute code `demo`, password `demo1234`
for users `admin`, `sana` (teacher), `rashid` (parent of two), `ahmed` (student)) with 32 students,
attendance since September, six months of fees, four exams (First Term published with marks), an
annual result being prepared, a full timetable, a week of homework, staff salaries and parent messages
waiting in the outbox, plus its own logo and blue theme. Running it again replaces
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
| CRUD | `/api/timetable/periods/` (+ POST `generate/`), `/api/timetable/entries/` (`?section=` or `?teacher=me`) | admin; teachers read |
| GET | `/api/me/timetable/` (`?student=` for parents) | parent / student |
| CRUD | `/api/homework/` (`?section=&date=`), GET `/api/homework/sections/` | admin / teacher |
| GET | `/api/me/homework/` (`?student=` for parents) | parent / student |
| GET/PATCH | `/api/messages/settings/` | institute admin |
| GET/DELETE | `/api/messages/` (`?status=&kind=`); POST `<id>/mark-sent/`, `send-pending/`, `fee-reminders/`, `notice/`, `test/` | institute admin |
| CRUD | `/api/payroll/employees/`; `/api/payroll/payslips/` (`?period=`; POST `generate/`, `<id>/pay/`, `<id>/unpay/`) | institute admin |
| GET | `/api/me/payslips/` | teacher / admin |
| GET | `/api/fees/receipts/<payment id>/` | admin / parent / student (own) |
| GET/POST | `/api/public/admissions/<code>/` | public |
| GET/PATCH/DELETE | `/api/admissions/` (`?status=`); POST `<id>/approve/`, `<id>/reject/` | institute admin |
| GET | `/api/students/id-cards/` (`?section=` or `?ids=`) | admin / teacher |
| GET/POST | `/api/push/` (subscribe; `action`: `test`, `unsubscribe`) | logged-in institute users |
| GET | `/api/platform/overview/` | super admin |
| GET | `/api/platform/backup/` (download `.json.gz`) | super admin |
| GET | `/api/institute/backup/`, `/api/institute/backup/excel/`, `/api/institute/backup/status/` | institute admin |
| GET | `/api/platform/tenants/<id>/backup/`; POST `.../restore/` (multipart `file`, optional `confirm_code`) | super admin |
| POST | `/api/institute/backup/restore/`; GET/POST `/api/institute/backup/snapshots/`, `.../snapshots/<sid>/` (put back) | institute admin |
| GET/POST | `/api/platform/tenants/<id>/snapshots/`, `.../snapshots/<sid>/` (download / put back with `confirm_code`) | super admin |
| GET | `/api/recycle-bin/`; POST/DELETE `/api/recycle-bin/<id>/` (restore / delete for good) | institute admin |
| GET | `/api/public/agreements/trial/` | public |
| GET/POST | `/api/agreements/` (sign), `/api/agreements/preview/?plan=&cycle=`, POST `/api/agreements/accept-trial/` | institute admin |
| GET/POST | `/api/agreements/<id>/` (`payment_reference`, `action: cancel`) | institute admin |
| GET/PATCH | `/api/platform/profile/`; GET `/api/platform/agreements/` (`?tenant=&status=`), `/api/platform/agreements/<id>/` | super admin |
| GET/POST | `/api/pay/stripe/return/`, `/api/pay/stripe/webhook/<code>/`, `/api/pay/safepay/return/` | gateways (public) |
| GET/POST | `/api/students/promotion/` (`?section=&to_session=`) | institute admin |
| GET/POST/DELETE | `/api/certificates/` (`?student=`) | institute admin |
| GET/PATCH | `/api/institute/settings/` (incl. `logo`, `brand_color`; read `brand`) | institute admin |
| GET | `/api/reports/<students|attendance|fee-dues|fee-collection|exam-result|payroll>/` (`&download=xlsx`) | institute admin |
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
-> ~~combined (weighted) annual result and parent/student results~~
-> ~~timetable~~ -> ~~homework & diary~~ -> ~~SMS/WhatsApp alerts~~ -> ~~staff & payroll~~ -> ~~reports (Excel/PDF)~~
-> ~~promotion~~ -> ~~subject teacher marks entry~~ -> ~~certificates~~ -> ~~white-label (logo, colour)~~
-> ~~fee receipts~~ -> ~~online admissions~~ -> ~~ID cards~~ -> ~~platform dashboard~~ -> ~~PWA + notifications~~
-> ~~Safepay, Stripe~~. Later: library, transport.
