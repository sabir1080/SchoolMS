"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Icon } from "@/components/Icon";
import { api, formatMoney } from "@/lib/api";
import { useAuth } from "@/lib/auth";

/** The platform owner's own guide (Roman Urdu), with a technical appendix for any developer they hire. */

interface PublicPlan {
  code: string;
  name: string;
  max_students: number | null;
  max_staff: number | null;
  feature_labels: string[];
  prices: { currency: string; billing_cycle: string; amount: string }[];
}

interface Part {
  id: string;
  icon: string;
  title: string;
  intro?: string;
  steps?: string[];
  points?: [string, string][];
  note?: string;
}

const PARTS: Part[] = [
  {
    id: "role",
    icon: "star",
    title: "Aap ka kirdar: platform owner",
    intro:
      "SchoolMS aik SaaS hai: aap bohat se schools ko app kiraye (subscription) par dete hain. Har school ka apna data, apne users aur apna admin hota hai. Aap sab schools ke upar hain.",
    points: [
      ["Aap ka login", "/platform/login par owner username aur password. Ye kisi ko na batayein."],
      ["Aap ke pages", "Overview (dashboard aur backup), Institutes (schools, payments, passwords) aur ye Owner guide."],
      ["School ka admin", "Har school ka apna admin hota hai jo apna sara kaam khud karta hai (bachche, fees, imtihan)."],
    ],
  },
  {
    id: "weekly",
    icon: "check",
    title: "Har hafte ke 5 minute (zaroori)",
    steps: [
      "Overview kholein. Sab se upar “Backup of all data” → Download backup dabayein.",
      "Download hui file (schoolms-backup-tareekh.json.gz) Google Drive mein upload kar dein. Purani files bhi rehne dein.",
      "“Renewals due in 14 days” dekhein: un schools ko phone/WhatsApp karke renewal yaad dilayein.",
      "“Expired — follow up” dekhein: jin ki subscription khatam hai un se raabta karein.",
      "Revenue tiles se is mahine ki aamdani dekh lein.",
    ],
    note: "Backup card laal ho jaye (7 din se zyada) to foran backup lein.",
  },
  {
    id: "new-school",
    icon: "rocket",
    title: "Naya school shamil karna",
    intro: "Do tareeqe hain. Dono mein school ko 14 din ka free trial milta hai (Pro plan ke features ke saath).",
    steps: [
      "Tareeqa 1 (school khud): school ko link dein; woh login page par “New institute? Register” se khud account bana leta hai.",
      "Tareeqa 2 (aap banayein): Institutes → Add institute (starts on a free trial) → naam, institute code, type, mulk, currency, timezone aur pehle admin ka username/email/password → Create institute.",
      "School ko ye teen cheezein bhejein: app ka link, institute code, aur admin ka username/password.",
      "School ko User manual ka link bhi bhejein (login page aur menu mein “Help & manual”).",
    ],
    note: "Institute code baad mein nahi badalta, is liye chhota aur saaf rakhein (maslan alhuda-lhr).",
  },
  {
    id: "payment",
    icon: "wallet",
    title: "School se paisa lena aur subscription barhana",
    steps: [
      "Pehli dafa: Business details mein apna business naam, pata aur “How institutes pay you” (bank account, JazzCash/Easypaisa) likh dein. Ye har agreement aur payment screen par aata hai.",
      "School ka admin Plan & Billing mein plan chunta hai, agreement form bhar kar apna naam likh kar sign karta hai, aur aap ko payment karta hai.",
      "Overview par “Agreements waiting for payment” mein woh school nazar aata hai (school ka diya hua payment reference bhi).",
      "Paisa aa jaye to Open → Amount, Method aur Reference check karein → Record payment.",
      "Plan chalu ho jata hai, muddat 30 din (monthly) ya 365 din (yearly) barh jati hai, aur agreement “Active” ho jata hai: paid period aur payment ki tafseel ke saath. School aur aap dono use print kar sakte hain.",
      "Institutes → Manage mein har school ke tamam agreements aur payment history nazar aati hai.",
    ],
    note: "Expire hone par school ka data mehfooz rehta hai; bas woh sirf Plan & Billing dekh sakta hai jab tak renew na ho.",
  },
  {
    id: "support",
    icon: "tool",
    title: "Schools ki madad (support)",
    points: [
      ["Admin password bhool gaya", "Institutes → Manage → Reset admin password → naya password likh kar school ko bata dein."],
      ["Teacher/parent password", "Ye kaam school ka admin khud karta hai: Users → Reset password."],
      ["School band karna", "Institutes → Suspend. Koi login nahi kar sakta, data mehfooz rehta hai. Wapas kholne ke liye Activate."],
      ["“Institute code not found”", "School ko sahi code batayein (Institutes list mein “Code:” likha hota hai)."],
      ["“Your login has expired”", "Ye normal hai: 7 din baad dobara sign in karna hota hai."],
      ["App pehli dafa der se khulti hai", "Free server so jata hai; aik minute mein jaag jata hai. Paid plan se ye khatam ho jata hai."],
    ],
  },
  {
    id: "payments-schools",
    icon: "card",
    title: "Schools ki online fees (JazzCash, Easypaisa, Safepay, Stripe)",
    intro:
      "Parents ki fees ka paisa seedha school ke apne merchant account mein jata hai, aap ke account mein nahi. Har school ko apna merchant account khud lena hota hai.",
    steps: [
      "School gateway (maslan JazzCash) se merchant account banwaye; gateway use keys deta hai.",
      "School admin: Institute settings → Online fee payments → keys bharein, Test mode on rakh kar aik test payment karein.",
      "Gateway account live kar de to Test mode band karein aur Show to parents tick karein.",
      "Ye feature sirf Pro aur Enterprise plan mein hai.",
    ],
    note: "Payment tabhi “paid” hoti hai jab gateway khud tasdeeq kare. Asli keys ke saath pehli payment zaroor test karwayein.",
  },
  {
    id: "demo",
    icon: "home",
    title: "Demo school (clients ko dikhane ke liye)",
    points: [
      ["Login", "Institute code demo · password demo1234 · users: admin, sana (teacher), rashid (parent), ahmed (student)."],
      ["Naam", "Bright Future Academy, apne logo aur neele rang ke saath."],
      ["Dobara naya karna", "Clients ke sath khel kar demo bigar jaye to Claude se kahein: “Demo data dobara seed kar dein”."],
    ],
  },
  {
    id: "backup",
    icon: "cloud",
    title: "Backup aur data wapas lana",
    points: [
      ["Pura backup", "Overview → Download backup. Aik file mein tamam schools ka sara data."],
      ["Aik school ka backup", "Institutes → school ka Manage → Download this institute's backup. Schools khud bhi Institute settings → Data backup se apni file (bina payment keys) aur Excel le sakte hain."],
      ["Kahan rakhein", "Google Drive (ya koi aur mehfooz jagah). File private hai: is mein passwords ke hash aur payment keys hain. Kisi ko na bhejein."],
      ["Sirf aik school wapas lana", "Institutes → Manage → Restore this institute: school ki file ya pura backup chunein → Check file (pehle/baad ki ginti dikhti hai) → institute code likhein → Restore now. Baqi schools, plan, payments aur agreements nahi badalte."],
      ["Restore undo", "Har restore se pehle us school ka mojooda data “Copies saved before a restore” mein mehfooz hota hai (aakhri 5). Put back dabayein aur code likhein to pehle wala data wapas."],
      ["Recycle bin", "Schools ki delete ki hui cheezen 30 din unke Recycle bin mein rehti hain; school admin khud Restore kar sakta hai."],
      ["Sab kuch wapas lana", "Agar pura database kharab ho jaye: Claude ko pura backup dein aur kahein “is backup se data restore kar dein”. Ye sirf khaali database mein hota hai."],
      ["Khud-ba-khud backup", "Free plan par mumkin nahi. Render paid plan lein to Claude rozana automatic backup laga sakta hai."],
    ],
  },
  {
    id: "hosting",
    icon: "globe",
    title: "App kahan chal rahi hai (hosting)",
    points: [
      ["Website (frontend)", "Render static site schoolms-web: https://schoolms-web-vzpe.onrender.com"],
      ["Server (API)", "Render web service schoolms-api: https://schoolms-api-viji.onrender.com"],
      ["Database", "Neon (PostgreSQL). Sara data yahan hai."],
      ["Code", "GitHub repository sabir1080/SchoolMS, branch ccr-3b156a9c-h1tcsc. Is branch par push hote hi Render khud naya version laga deta hai."],
      ["Kharcha", "Abhi sab free plans par hai. Asli schools ke liye Render ka paid plan (taqreeban 7 dollar mahana server ke liye) mashwara hai taake app na soye."],
      ["Apna domain", "Maslan app.yourschoolms.com: domain khareed kar Claude se kahein, woh Render par jor dega."],
    ],
  },
  {
    id: "claude",
    icon: "chat",
    title: "Claude se kaam kaise karwayen",
    intro: "Aap ko koi technical kaam nahi karna. Bas saaf likh kar batayein; Claude banata, test karta, deploy karta aur Roman Urdu mein report deta hai.",
    points: [
      ["Naya feature", "“Library ka feature bana dein: kitaben, issue/return aur late fine.”"],
      ["Bug", "“Parent ke phone par fees ka button nahi aa raha” — saath screenshot bhej dein."],
      ["Demo", "“Demo data dobara seed kar dein.”"],
      ["Restore", "Aik school: Institutes → Manage → Restore this institute (khud). Pura database: “Is backup file se data restore kar dein.” (file saath bhejein)"],
      ["Sawal", "“Abhi kaun se kaam baqi hain?” ya “Is mahine kitne schools expire hue?”"],
    ],
  },
  {
    id: "safety",
    icon: "shield",
    title: "Hifazat ke usool",
    steps: [
      "Owner password mazboot rakhein aur kisi ko na batayein; zaroorat ho to Change password se badlein.",
      "Backup file sirf apni Google Drive mein rakhein.",
      "Render, Neon aur GitHub ke account passwords mehfooz rakhein; in par two-factor login on karein.",
      "Kisi school ka data doosre school ko kabhi nazar nahi aata; app har request par ye check karti hai.",
    ],
  },
];

const TECH: [string, string][] = [
  ["Stack", "Backend Django 5.2 + Django REST Framework + SimpleJWT, PostgreSQL (Neon). Frontend Next.js 15 static export + Tailwind CSS v4."],
  ["Repository", "sabir1080/SchoolMS · deploy branch ccr-3b156a9c-h1tcsc · rules for contributors in CLAUDE.md, full feature/API list in README.md."],
  ["Structure", "backend/apps/* (one Django app per module: tenants, accounts, subscriptions, academics, students, attendance, fees, payments, exams, timetable, homework, messaging, payroll, reports, certificates, admissions, agreements, backups, recyclebin) · frontend/src/app (pages), src/components, src/lib."],
  ["Multi-tenancy", "Institute data inherits TenantScopedModel; viewsets use TenantScopedViewSetMixin + required_feature (plan gating)."],
  ["API env vars (names only)", "SECRET_KEY, DEBUG, DATABASE_URL, CORS_ALLOWED_ORIGINS, FRONTEND_URL, SUPERADMIN_USERNAME, SUPERADMIN_PASSWORD, VAPID_PRIVATE_KEY, TRIAL_PLAN_CODE, TRIAL_DAYS, PLATFORM_TIMEZONE. Never print their values."],
  ["Web env vars", "NEXT_PUBLIC_API_URL (the API address)."],
  ["Run tests", "cd backend && pytest (SQLite) and TEST_DATABASE_URL=postgres://… pytest (throwaway PostgreSQL) · cd frontend && npm run lint && npx tsc --noEmit && npm run build · Playwright browser runs on mobile and desktop."],
  ["Useful commands", "python manage.py seed_demo · create_backup <file> · restore_backup <file> · generate_vapid_keys · ensure_superadmin."],
  ["Deploy", "Push to the deploy branch; Render builds both services (build.sh runs migrations). Free plan has no shell: one-off jobs run via build.sh with a commit-gated env var (see CLAUDE.md)."],
  ["Payments", "A gateway payment is recorded only after server-side verification (hash, read-back, signed webhook or IPN)."],
];

export default function OwnerGuidePage() {
  const { user } = useAuth();
  const [plans, setPlans] = useState<PublicPlan[]>([]);

  useEffect(() => {
    api<PublicPlan[]>("/api/public/plans/", {}, false)
      .then(setPlans)
      .catch(() => setPlans([]));
  }, []);

  if (user?.role !== "super_admin") return <p className="text-sm text-slate-500">This guide is for the platform owner.</p>;

  return (
    <div className="max-w-4xl space-y-5">
      <div className="overflow-hidden rounded-2xl bg-gradient-to-br from-brand-700 via-brand-600 to-brand-800 p-6 text-white">
        <p className="text-xs font-medium tracking-wide uppercase opacity-80">Sirf platform owner ke liye</p>
        <h1 className="mt-1 text-2xl font-bold md:text-3xl">Owner guide</h1>
        <p className="mt-2 max-w-2xl text-sm text-white/85">
          SchoolMS ko business ki tarah chalane ki mukammal rehnumai: schools shamil karna, paisa lena, support, backup, hosting, aur Claude se
          kaam karwana. Aakhir mein developer ke liye technical hissa hai.
        </p>
        <div className="mt-4 flex flex-wrap gap-2 text-xs">
          {PARTS.map((p) => (
            <a key={p.id} href={`#${p.id}`} className="rounded-full bg-white/15 px-3 py-1 hover:bg-white/25">
              {p.title.split(":")[0]}
            </a>
          ))}
          <a href="#plans" className="rounded-full bg-white/15 px-3 py-1 hover:bg-white/25">
            Plans
          </a>
          <a href="#tech" className="rounded-full bg-white/15 px-3 py-1 hover:bg-white/25">
            Developer
          </a>
        </div>
      </div>

      {PARTS.map((p) => (
        <section key={p.id} id={p.id} className="scroll-mt-4 rounded-2xl bg-white p-5 shadow-sm md:p-6 dark:bg-slate-900" data-testid="guide-section">
          <div className="flex items-center gap-3">
            <span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-700 dark:bg-brand-950">
              <Icon name={p.icon} />
            </span>
            <h2 className="text-lg font-semibold">{p.title}</h2>
          </div>
          {p.intro && <p className="mt-3 text-sm text-slate-600 dark:text-slate-300">{p.intro}</p>}
          {p.steps && (
            <ol className="mt-4 space-y-3">
              {p.steps.map((s, i) => (
                <li key={i} className="flex gap-3 text-sm leading-relaxed">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-600 text-xs font-bold text-white">{i + 1}</span>
                  <span>{s}</span>
                </li>
              ))}
            </ol>
          )}
          {p.points && (
            <dl className="mt-4 grid gap-3 sm:grid-cols-2">
              {p.points.map(([k, v]) => (
                <div key={k} className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                  <dt className="text-sm font-semibold">{k}</dt>
                  <dd className="mt-1 text-sm break-words text-slate-600 dark:text-slate-300">{v}</dd>
                </div>
              ))}
            </dl>
          )}
          {p.note && (
            <p className="mt-4 rounded-xl bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:bg-amber-950 dark:text-amber-200">{p.note}</p>
          )}
        </section>
      ))}

      <section id="plans" className="scroll-mt-4 rounded-2xl bg-white p-5 shadow-sm md:p-6 dark:bg-slate-900">
        <h2 className="text-lg font-semibold">Plans aur qeematein (abhi server par)</h2>
        <p className="mt-1 text-sm text-slate-500">Qeematein ya features badalne hon to Claude se kahein.</p>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          {plans.map((plan) => (
            <div key={plan.code} className="rounded-xl border border-slate-200 p-4 dark:border-slate-700" data-testid="guide-plan">
              <p className="font-semibold">{plan.name}</p>
              <p className="text-xs text-slate-500">
                {plan.max_students ? `${plan.max_students} students` : "Unlimited students"} · {plan.max_staff ? `${plan.max_staff} staff` : "unlimited staff"}
              </p>
              <ul className="mt-2 space-y-0.5 text-sm">
                {plan.prices
                  .filter((p) => p.currency === "PKR")
                  .map((p) => (
                    <li key={p.billing_cycle}>
                      {formatMoney(p.amount, p.currency)} / {p.billing_cycle === "yearly" ? "year" : "month"}
                    </li>
                  ))}
              </ul>
              <p className="mt-2 text-xs text-slate-500">{plan.feature_labels.join(" · ")}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="tech" className="scroll-mt-4 rounded-2xl bg-slate-900 p-5 text-slate-100 shadow-sm md:p-6">
        <div className="flex items-center gap-3">
          <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-white/10">
            <Icon name="tool" />
          </span>
          <div>
            <h2 className="text-lg font-semibold">For developers (technical appendix)</h2>
            <p className="text-xs text-slate-400">Give this part to any developer who works on SchoolMS.</p>
          </div>
        </div>
        <dl className="mt-4 space-y-3">
          {TECH.map(([k, v]) => (
            <div key={k} className="grid gap-1 sm:grid-cols-[180px_1fr]">
              <dt className="text-sm font-semibold text-white">{k}</dt>
              <dd className="font-mono text-xs leading-relaxed break-words text-slate-300">{v}</dd>
            </div>
          ))}
        </dl>
      </section>

      <p className="text-center text-xs text-slate-500">
        <Link href="/platform/overview" className="hover:underline">
          Overview
        </Link>{" "}
        ·{" "}
        <Link href="/manual" className="hover:underline">
          User manual
        </Link>{" "}
        ·{" "}
        <Link href="/about" className="hover:underline">
          About
        </Link>
      </p>
    </div>
  );
}
