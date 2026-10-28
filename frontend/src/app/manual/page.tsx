"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { Icon } from "@/components/Icon";
import { useAuth } from "@/lib/auth";
import { AUDIENCE_BADGE, AUDIENCES, FAQ, MANUAL, type Audience, type Lang } from "@/lib/manual";

const LANG_KEY = "sms_manual_lang";

const UI = {
  en: {
    title: "User manual",
    subtitle: "How to use SchoolMS, step by step. Choose your role to see only what you need.",
    search: "Search the manual…",
    contents: "Contents",
    faq: "Common questions",
    none: "Nothing found. Try another word.",
    back: "Back to the app",
    login: "Log in",
    tip: "Tip",
  },
  ur: {
    title: "User manual",
    subtitle: "SchoolMS chalane ka tareeqa, qadam ba qadam. Apna kirdar chunein taake sirf zaroori hissa nazar aaye.",
    search: "Manual mein dhoondein…",
    contents: "Fehrist",
    faq: "Aam sawalat",
    none: "Kuch nahi mila. Koi aur lafz likhein.",
    back: "App par wapas",
    login: "Log in",
    tip: "Mashwara",
  },
};

function shows(audience: Audience, filter: Audience | "every") {
  if (filter === "every" || audience === "all") return true;
  return audience === filter;
}

export default function ManualPage() {
  const { user } = useAuth();
  const [lang, setLang] = useState<Lang>("en");
  const [filter, setFilter] = useState<Audience | "every">("every");
  const [query, setQuery] = useState("");
  // Contents stay open beside the text on wide screens; on phones they start closed so the manual comes first.
  const [tocOpen, setTocOpen] = useState(true);
  const t = UI[lang];

  useEffect(() => {
    setTocOpen(window.matchMedia("(min-width: 1024px)").matches);
    try {
      const saved = localStorage.getItem(LANG_KEY);
      if (saved === "en" || saved === "ur") setLang(saved);
    } catch {
      /* private mode */
    }
  }, []);

  // Start with the reader's own role when they are logged in.
  useEffect(() => {
    if (user?.role === "teacher") setFilter("teacher");
    else if (user?.role === "parent" || user?.role === "student") setFilter("family");
    else if (user?.role === "admin") setFilter("admin");
  }, [user]);

  function chooseLang(value: Lang) {
    setLang(value);
    try {
      localStorage.setItem(LANG_KEY, value);
    } catch {
      /* private mode */
    }
  }

  const sections = useMemo(() => {
    const q = query.trim().toLowerCase();
    return MANUAL.filter((s) => shows(s.audience, filter)).filter(
      (s) => !q || [s.title[lang], s.intro[lang], ...s.steps[lang], s.tip?.[lang] ?? ""].join(" ").toLowerCase().includes(q),
    );
  }, [filter, query, lang]);

  return (
    <main className="min-h-screen">
      <header className="bg-gradient-to-br from-brand-700 via-brand-600 to-brand-800 text-white">
        <div className="mx-auto max-w-6xl px-4 pt-6 pb-10">
          <nav className="flex items-center justify-between gap-3 text-sm">
            <Link href="/about" className="flex items-center gap-2 font-semibold">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/icons/icon-192.png" alt="" className="h-8 w-8 rounded-lg" />
              SchoolMS
            </Link>
            <span className="flex items-center gap-3">
              <span className="flex rounded-full bg-white/15 p-0.5 text-xs font-medium" role="group" aria-label="Language">
                {(["en", "ur"] as Lang[]).map((l) => (
                  <button
                    key={l}
                    type="button"
                    onClick={() => chooseLang(l)}
                    aria-pressed={lang === l}
                    className={`rounded-full px-3 py-1 ${lang === l ? "bg-white text-brand-700" : "text-white"}`}
                  >
                    {l === "en" ? "English" : "Roman Urdu"}
                  </button>
                ))}
              </span>
              <Link href={user ? "/dashboard" : "/login"} className="hidden hover:underline sm:inline">
                {user ? t.back : t.login}
              </Link>
            </span>
          </nav>
          <h1 className="mt-8 text-3xl font-bold md:text-4xl">{t.title}</h1>
          <p className="mt-2 max-w-2xl text-white/85">{t.subtitle}</p>
          <div className="mt-6 flex flex-wrap gap-2">
            {AUDIENCES.map((a) => (
              <button
                key={a.value}
                type="button"
                onClick={() => setFilter(a.value)}
                aria-pressed={filter === a.value}
                className={`rounded-full px-4 py-1.5 text-sm font-medium ${
                  filter === a.value ? "bg-white text-brand-700" : "bg-white/15 text-white hover:bg-white/25"
                }`}
              >
                {a.label[lang]}
              </button>
            ))}
          </div>
          <label className="relative mt-4 block max-w-xl">
            <span className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-slate-400">
              <Icon name="search" className="h-4 w-4" />
            </span>
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t.search}
              aria-label={t.search}
              className="w-full rounded-xl border-0 bg-white py-2.5 pr-3 pl-9 text-sm text-slate-900 shadow-sm outline-none"
            />
          </label>
        </div>
      </header>

      <div className="mx-auto grid max-w-6xl gap-6 px-4 py-8 lg:grid-cols-[230px_1fr]">
        <aside className="lg:sticky lg:top-4 lg:self-start">
          <details
            className="rounded-2xl bg-white p-4 shadow-sm dark:bg-slate-900"
            open={tocOpen}
            onToggle={(e) => setTocOpen((e.target as HTMLDetailsElement).open)}
          >
            <summary className="cursor-pointer text-sm font-semibold">{t.contents}</summary>
            <ol className="mt-2 space-y-1 text-sm">
              {sections.map((s) => (
                <li key={s.id}>
                  <a href={`#${s.id}`} className="flex items-center gap-2 rounded-lg px-2 py-1 text-slate-600 hover:bg-brand-50 hover:text-brand-700 dark:text-slate-300 dark:hover:bg-brand-950">
                    <Icon name={s.icon} className="h-4 w-4 shrink-0" />
                    <span className="truncate">{s.title[lang]}</span>
                  </a>
                </li>
              ))}
              <li>
                <a href="#faq" className="flex items-center gap-2 rounded-lg px-2 py-1 text-slate-600 hover:bg-brand-50 hover:text-brand-700 dark:text-slate-300 dark:hover:bg-brand-950">
                  <Icon name="alert" className="h-4 w-4 shrink-0" />
                  {t.faq}
                </a>
              </li>
            </ol>
          </details>
        </aside>

        <div className="min-w-0 space-y-5">
          {sections.length === 0 && <p className="rounded-2xl bg-white p-6 text-sm text-slate-500 shadow-sm dark:bg-slate-900">{t.none}</p>}
          {sections.map((s) => (
            <section key={s.id} id={s.id} className="scroll-mt-4 rounded-2xl bg-white p-5 shadow-sm md:p-6 dark:bg-slate-900" data-testid="manual-section">
              <div className="flex items-start gap-3">
                <span className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-700 dark:bg-brand-950">
                  <Icon name={s.icon} />
                </span>
                <div className="min-w-0">
                  <h2 className="text-lg font-semibold">{s.title[lang]}</h2>
                  <span className="mt-0.5 inline-block rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                    {AUDIENCE_BADGE[s.audience][lang]}
                  </span>
                </div>
              </div>
              <p className="mt-3 text-sm text-slate-600 dark:text-slate-300">{s.intro[lang]}</p>
              <div className={s.images ? "mt-4 grid gap-5 md:grid-cols-[1fr_200px]" : "mt-4"}>
                <ol className="space-y-3">
                  {s.steps[lang].map((step, i) => (
                    <li key={i} className="flex gap-3 text-sm leading-relaxed">
                      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-600 text-xs font-bold text-white">{i + 1}</span>
                      <span>{step}</span>
                    </li>
                  ))}
                </ol>
                {s.images && (
                  <div className="flex gap-4 overflow-x-auto pb-1 md:flex-col md:overflow-visible">
                    {s.images.map((img) => (
                      <figure key={img.file} className="w-52 shrink-0 md:w-full">
                        <a href={`/manual/${img.file}.jpg`} target="_blank" rel="noreferrer" className="block">
                          {/* Static screenshots shipped with the site; next/image is not available in the static export. */}
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img
                            src={`/manual/${img.file}.jpg`}
                            alt={img.caption[lang]}
                            width={390}
                            height={760}
                            loading="lazy"
                            className="h-auto w-full rounded-2xl border-4 border-slate-800 bg-white shadow-md dark:border-slate-600"
                          />
                        </a>
                        <figcaption className="mt-1.5 text-center text-xs text-slate-500">{img.caption[lang]}</figcaption>
                      </figure>
                    ))}
                  </div>
                )}
              </div>
              {s.tip && (
                <p className="mt-4 rounded-xl bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:bg-amber-950 dark:text-amber-200">
                  <span className="font-semibold">{t.tip}: </span>
                  {s.tip[lang]}
                </p>
              )}
            </section>
          ))}

          <section id="faq" className="scroll-mt-4 rounded-2xl bg-white p-5 shadow-sm md:p-6 dark:bg-slate-900">
            <h2 className="text-lg font-semibold">{t.faq}</h2>
            <div className="mt-3 divide-y divide-slate-100 dark:divide-slate-800">
              {FAQ.map((f) => (
                <details key={f.q.en} className="group py-3">
                  <summary className="cursor-pointer list-none text-sm font-medium">
                    <span className="mr-2 inline-block text-brand-600 transition group-open:rotate-90">›</span>
                    {f.q[lang]}
                  </summary>
                  <p className="mt-2 pl-5 text-sm text-slate-600 dark:text-slate-300">{f.a[lang]}</p>
                </details>
              ))}
            </div>
          </section>
          <p className="text-center text-xs text-slate-500">
            <Link href="/about" className="hover:underline">
              About SchoolMS
            </Link>{" "}
            ·{" "}
            <Link href={user ? "/dashboard" : "/login"} className="hover:underline">
              {user ? t.back : t.login}
            </Link>
          </p>
        </div>
      </div>
    </main>
  );
}
