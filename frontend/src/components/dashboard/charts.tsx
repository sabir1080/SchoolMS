"use client";

import { useState } from "react";

/** Round a max value up to a clean axis top: 1, 2, 2.5, 5 x 10^n. */
function niceMax(value: number) {
  if (value <= 0) return 1;
  const power = 10 ** Math.floor(Math.log10(value));
  for (const step of [1, 2, 2.5, 5, 10]) if (value <= step * power) return step * power;
  return 10 * power;
}

export function compact(n: number) {
  if (n >= 1_000_000) return `${+(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${+(n / 1_000).toFixed(1)}K`;
  return String(Math.round(n));
}

function TableToggle({ open, onToggle }: { open: boolean; onToggle: () => void }) {
  return (
    <button type="button" onClick={onToggle} className="text-xs text-brand-600 hover:underline">
      {open ? "Show chart" : "Show as table"}
    </button>
  );
}

/** The hover/focus readout above a chart: the value leads, the label follows. */
function Readout({ children }: { children: React.ReactNode }) {
  return <div className="min-h-10 text-sm" aria-live="polite">{children}</div>;
}

interface Column {
  key: string;
  label: string;
  value: number | null;
  detail?: string;
}

/** One series of columns on a 0-100% scale (e.g. daily attendance). */
export function PercentColumns({ title, columns, emptyText }: { title: string; columns: Column[]; emptyText: string }) {
  const [active, setActive] = useState<number | null>(null);
  const [table, setTable] = useState(false);
  const shown = active ?? columns.length - 1;
  const current = columns[shown];

  return (
    <div>
      <div className="flex items-center justify-between gap-2">
        <h2 className="font-medium">{title}</h2>
        {columns.length > 0 && <TableToggle open={table} onToggle={() => setTable(!table)} />}
      </div>
      {columns.length === 0 ? (
        <p className="mt-2 text-sm text-slate-500">{emptyText}</p>
      ) : table ? (
        <table className="mt-2 w-full text-sm tabular-nums">
          <tbody>
            {columns.map((c) => (
              <tr key={c.key} className="border-b border-slate-100 dark:border-slate-800">
                <td className="py-1">{c.label}</td>
                <td className="py-1 text-right font-medium">{c.value === null ? "—" : `${c.value}%`}</td>
                <td className="py-1 pl-3 text-right text-xs text-slate-500">{c.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <>
          <Readout>
            {current && (
              <>
                <span className="text-lg font-semibold">{current.value === null ? "—" : `${current.value}%`}</span>{" "}
                <span className="text-slate-500">
                  {current.label}
                  {current.detail && ` · ${current.detail}`}
                </span>
              </>
            )}
          </Readout>
          <div className="relative mt-3 h-40" onMouseLeave={() => setActive(null)}>
            {[100, 50, 0].map((tick) => (
              <div
                key={tick}
                className="absolute inset-x-0 flex translate-y-1/2 items-center"
                style={{ bottom: `${tick}%` }}
              >
                <span className="w-9 pr-1 text-right text-[10px] text-slate-400 tabular-nums">{tick}%</span>
                <div className="h-px flex-1" style={{ background: "var(--chart-grid)" }} />
              </div>
            ))}
            <div className="absolute inset-y-0 right-0 left-9 flex items-end gap-0.5">
              {columns.map((c, i) => (
                <button
                  key={c.key}
                  type="button"
                  onMouseEnter={() => setActive(i)}
                  onFocus={() => setActive(i)}
                  onBlur={() => setActive(null)}
                  aria-label={`${c.label}: ${c.value === null ? "no data" : `${c.value}%`}`}
                  className="flex h-full flex-1 items-end justify-center focus:outline-none"
                >
                  <span
                    className="block w-full max-w-6 rounded-t transition-opacity"
                    style={{
                      height: `${Math.max(c.value ?? 0, 0.5)}%`,
                      background: "var(--series-1)",
                      opacity: active === null || active === i ? 1 : 0.45,
                    }}
                  />
                </button>
              ))}
            </div>
          </div>
          <div className="mt-1 flex justify-between pl-9 text-[10px] text-slate-400">
            <span>{columns[0]?.label}</span>
            <span>{columns[columns.length - 1]?.label}</span>
          </div>
        </>
      )}
    </div>
  );
}

interface Group {
  key: string;
  label: string;
  values: [number, number];
}

/** Two series side by side per group (e.g. fees billed vs received per month). */
export function PairedColumns({
  title,
  seriesNames,
  groups,
  format,
}: {
  title: string;
  seriesNames: [string, string];
  groups: Group[];
  format: (n: number) => string;
}) {
  const [active, setActive] = useState<number | null>(null);
  const [table, setTable] = useState(false);
  const max = niceMax(Math.max(0, ...groups.flatMap((g) => g.values)));
  const shown = active ?? groups.length - 1;
  const current = groups[shown];
  const colors = ["var(--series-1)", "var(--series-2)"];

  return (
    <div>
      <div className="flex items-center justify-between gap-2">
        <h2 className="font-medium">{title}</h2>
        <TableToggle open={table} onToggle={() => setTable(!table)} />
      </div>
      <div className="mt-1 flex gap-4 text-xs text-slate-600 dark:text-slate-300">
        {seriesNames.map((name, i) => (
          <span key={name} className="flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: colors[i] }} />
            {name}
          </span>
        ))}
      </div>
      {table ? (
        <table className="mt-2 w-full text-sm tabular-nums">
          <thead>
            <tr className="text-left text-xs text-slate-500">
              <th className="py-1 font-normal">Month</th>
              <th className="py-1 text-right font-normal">{seriesNames[0]}</th>
              <th className="py-1 text-right font-normal">{seriesNames[1]}</th>
            </tr>
          </thead>
          <tbody>
            {groups.map((g) => (
              <tr key={g.key} className="border-b border-slate-100 dark:border-slate-800">
                <td className="py-1">{g.label}</td>
                <td className="py-1 text-right">{format(g.values[0])}</td>
                <td className="py-1 text-right">{format(g.values[1])}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <>
          <Readout>
            {current && (
              <span className="flex flex-wrap gap-x-4">
                <span className="text-slate-500">{current.label}</span>
                {seriesNames.map((name, i) => (
                  <span key={name} className="flex items-center gap-1.5">
                    <span className="inline-block h-0.5 w-3" style={{ background: colors[i] }} />
                    <span className="font-semibold">{format(current.values[i])}</span>
                    <span className="text-slate-500">{name.toLowerCase()}</span>
                  </span>
                ))}
              </span>
            )}
          </Readout>
          <div className="relative mt-3 h-40" onMouseLeave={() => setActive(null)}>
            {[max, max / 2, 0].map((tick) => (
              <div
                key={tick}
                className="absolute inset-x-0 flex translate-y-1/2 items-center"
                style={{ bottom: `${(tick / max) * 100}%` }}
              >
                <span className="w-9 pr-1 text-right text-[10px] text-slate-400 tabular-nums">{compact(tick)}</span>
                <div className="h-px flex-1" style={{ background: "var(--chart-grid)" }} />
              </div>
            ))}
            <div className="absolute inset-y-0 right-0 left-9 flex items-end gap-2">
              {groups.map((g, i) => (
                <button
                  key={g.key}
                  type="button"
                  onMouseEnter={() => setActive(i)}
                  onFocus={() => setActive(i)}
                  onBlur={() => setActive(null)}
                  aria-label={`${g.label}: ${seriesNames[0]} ${format(g.values[0])}, ${seriesNames[1]} ${format(g.values[1])}`}
                  className="flex h-full flex-1 items-end justify-center gap-0.5 focus:outline-none"
                >
                  {g.values.map((v, s) => (
                    <span
                      key={s}
                      className="block w-full max-w-6 rounded-t"
                      style={{
                        height: `${Math.max((v / max) * 100, v > 0 ? 1 : 0)}%`,
                        background: colors[s],
                        opacity: active === null || active === i ? 1 : 0.45,
                      }}
                    />
                  ))}
                </button>
              ))}
            </div>
          </div>
          <div className="mt-1 flex gap-2 pl-9 text-[10px] text-slate-400">
            {groups.map((g) => (
              <span key={g.key} className="flex-1 text-center">
                {g.label}
              </span>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

/** Horizontal bars with the value at the tip (e.g. students per class). */
export function BarList({ title, rows, emptyText }: { title: string; rows: { key: string; label: string; value: number }[]; emptyText: string }) {
  const max = Math.max(1, ...rows.map((r) => r.value));
  return (
    <div>
      <h2 className="mb-2 font-medium">{title}</h2>
      {rows.length === 0 ? (
        <p className="text-sm text-slate-500">{emptyText}</p>
      ) : (
        <ul className="space-y-2">
          {rows.map((r) => (
            <li key={r.key} className="grid grid-cols-[6.5rem_1fr] items-center gap-2 text-sm">
              <span className="truncate text-slate-600 dark:text-slate-300" title={r.label}>
                {r.label}
              </span>
              <span className="flex items-center gap-2">
                <span
                  className="block h-4 rounded-r"
                  style={{ width: `${Math.max((r.value / max) * 100, 2)}%`, maxWidth: "calc(100% - 2.5rem)", background: "var(--series-1)" }}
                />
                <span className="font-medium tabular-nums">{r.value}</span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
