import Link from "next/link";

import { Icon } from "@/components/Icon";

export const metadata = { title: "About · SchoolMS", description: "School, college, coaching and tuition management in one app." };

const FEATURES: [string, string, string][] = [
  ["users", "Admissions & students", "Admission forms online or at the desk, parent logins, photos and ID cards."],
  ["check", "Attendance", "One tap per class; parents get an alert the same day a child is absent."],
  ["wallet", "Fees & receipts", "Monthly bills in one tap, discounts, receipts and reminders for dues."],
  ["card", "Online payments", "JazzCash, Easypaisa, Safepay and cards (Stripe) straight to the school's account."],
  ["clipboard", "Exams & report cards", "Date sheets, marks entry by subject teachers, positions, annual results."],
  ["calendar", "Timetable", "Periods and class timetables with clash checks; each teacher's week."],
  ["book", "Homework diary", "Teachers post homework; parents see it day by day."],
  ["chat", "Parent messages", "Free WhatsApp links or automatic SMS/WhatsApp, plus phone notifications."],
  ["briefcase", "Staff & payroll", "Salary slips for everyone in one tap; mark paid; teachers see their own."],
  ["chart", "Reports", "Student lists, attendance, fee dues and collection, results and salaries in Excel or PDF."],
  ["arrow", "Promotion & certificates", "Move a class to the next session; character, leaving and bonafide certificates."],
  ["palette", "Your own brand", "Your logo and colour on the login page, report cards, receipts and ID cards."],
];

const FOR: [string, string][] = [
  ["School", "Classes and sections"],
  ["College", "Programs and groups"],
  ["University", "Degree programs and batches"],
  ["Coaching center", "Courses and batches"],
  ["Tuition center", "Small groups, simple fees"],
];

const TRUST: [string, string, string][] = [
  ["shield", "Private by design", "Every institute sees only its own data, checked on every request."],
  ["card", "Verified payments", "A payment counts only after the gateway confirms it, never on a redirect alone."],
  ["cloud", "Backups", "One-tap full backups for the platform, with a tested restore."],
  ["phone", "Works on any phone", "Install it like an app, use it offline-friendly, get free notifications."],
];

export default function AboutPage() {
  return (
    <main className="min-h-screen">
      <section className="relative overflow-hidden bg-gradient-to-br from-brand-700 via-brand-600 to-brand-800 text-white">
        <div className="pointer-events-none absolute -top-24 -right-24 h-72 w-72 rounded-full bg-white/10 blur-2xl" />
        <div className="pointer-events-none absolute -bottom-32 -left-20 h-80 w-80 rounded-full bg-white/10 blur-3xl" />
        <div className="relative mx-auto max-w-5xl px-4 py-14 md:py-20">
          <nav className="mb-10 flex items-center justify-between text-sm">
            <span className="flex items-center gap-2 font-semibold">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/icons/icon-192.png" alt="" className="h-8 w-8 rounded-lg" />
              SchoolMS
            </span>
            <span className="flex gap-4">
              <Link href="/manual" className="hover:underline">
                User manual
              </Link>
              <Link href="/login" className="hover:underline">
                Log in
              </Link>
            </span>
          </nav>
          <p className="mb-3 inline-block rounded-full bg-white/15 px-3 py-1 text-xs font-medium tracking-wide uppercase">
            School management, made simple
          </p>
          <h1 className="max-w-3xl text-4xl leading-tight font-bold md:text-5xl">
            Run your whole institute from one app — on any phone.
          </h1>
          <p className="mt-4 max-w-2xl text-lg text-white/85">
            Admissions, attendance, fees, exams, timetable, homework, salaries and parent messages, for schools, colleges, universities,
            coaching and tuition centers.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/register" className="rounded-xl bg-white px-5 py-3 text-sm font-semibold text-brand-700 shadow-sm hover:bg-brand-50">
              Start free trial
            </Link>
            <Link href="/login?code=demo" className="rounded-xl border border-white/40 px-5 py-3 text-sm font-semibold hover:bg-white/10">
              Try the demo
            </Link>
          </div>
          <p className="mt-3 text-xs text-white/70">Demo: institute code demo · username admin · password demo1234</p>
        </div>
      </section>

      <section className="mx-auto max-w-5xl px-4 py-14">
        <h2 className="text-2xl font-bold">Everything a school needs</h2>
        <p className="mt-1 text-slate-500">Each part works on its own and together, so nothing is typed twice.</p>
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map(([icon, title, text]) => (
            <div key={title} className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-100 dark:bg-slate-900 dark:ring-slate-800">
              <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-brand-50 text-brand-700 dark:bg-brand-950">
                <Icon name={icon} />
              </span>
              <h3 className="mt-3 font-semibold">{title}</h3>
              <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{text}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-white py-14 dark:bg-slate-900">
        <div className="mx-auto max-w-5xl px-4">
          <h2 className="text-2xl font-bold">Made for every kind of institute</h2>
          <div className="mt-6 flex flex-wrap gap-3">
            {FOR.map(([name, note]) => (
              <div key={name} className="rounded-xl border border-slate-200 px-4 py-3 dark:border-slate-700">
                <p className="font-semibold">{name}</p>
                <p className="text-xs text-slate-500">{note}</p>
              </div>
            ))}
          </div>
          <p className="mt-4 text-sm text-slate-500">Call them classes, grades, programs or batches — the app uses your words.</p>
        </div>
      </section>

      <section className="mx-auto max-w-5xl px-4 py-14">
        <h2 className="text-2xl font-bold">Start in three steps</h2>
        <ol className="mt-8 grid gap-4 md:grid-cols-3">
          {[
            ["Register", "Create your institute and admin login in a minute. A free trial starts at once."],
            ["Set up", "Add your session, classes, subjects and fees. The dashboard shows what is left."],
            ["Invite", "Give teachers and parents their logins. Parents install the app and turn on notifications."],
          ].map(([title, text], i) => (
            <li key={title} className="relative rounded-2xl bg-white p-5 shadow-sm dark:bg-slate-900">
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-600 font-bold text-white">{i + 1}</span>
              <h3 className="mt-3 font-semibold">{title}</h3>
              <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{text}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="bg-slate-900 py-14 text-white">
        <div className="mx-auto max-w-5xl px-4">
          <h2 className="text-2xl font-bold">Safe and dependable</h2>
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {TRUST.map(([icon, title, text]) => (
              <div key={title}>
                <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-white/10">
                  <Icon name={icon} />
                </span>
                <h3 className="mt-3 font-semibold">{title}</h3>
                <p className="mt-1 text-sm text-white/70">{text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-5xl px-4 py-14 text-center">
        <h2 className="text-2xl font-bold">Ready to try it?</h2>
        <p className="mt-1 text-slate-500">Open the demo school or register your own institute.</p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <Link href="/register" className="rounded-xl bg-brand-600 px-5 py-3 text-sm font-semibold text-white hover:bg-brand-700">
            Start free trial
          </Link>
          <Link href="/manual" className="rounded-xl border border-slate-300 px-5 py-3 text-sm font-semibold dark:border-slate-700">
            Read the user manual
          </Link>
        </div>
      </section>

      <footer className="border-t border-slate-200 py-6 text-center text-xs text-slate-500 dark:border-slate-800">
        SchoolMS · <Link href="/manual" className="hover:underline">User manual</Link> ·{" "}
        <Link href="/login" className="hover:underline">Log in</Link>
      </footer>
    </main>
  );
}
