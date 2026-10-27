import type { InputHTMLAttributes, SelectHTMLAttributes } from "react";

import { ApiError } from "@/lib/api";

const fieldClass =
  "w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 text-sm outline-none focus:border-indigo-500 dark:border-slate-700";

export function Field({ label, ...props }: { label: string } & InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="block space-y-1">
      <span className="text-sm font-medium">{label}</span>
      <input className={fieldClass} {...props} />
    </label>
  );
}

export function SelectField({
  label,
  options,
  ...props
}: { label: string; options: [string, string][] } & SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <label className="block space-y-1">
      <span className="text-sm font-medium">{label}</span>
      <select className={`${fieldClass} dark:bg-slate-900`} {...props}>
        {options.map(([value, text]) => (
          <option key={value} value={value}>
            {text}
          </option>
        ))}
      </select>
    </label>
  );
}

export function Card({ children }: { children: React.ReactNode }) {
  return <div className="rounded-2xl bg-white p-4 shadow-sm md:p-6 dark:bg-slate-900">{children}</div>;
}

export function Button(props: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      className={`rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60 ${props.className ?? ""}`}
    />
  );
}

const FIELD_LABELS: Record<string, string> = {
  slug: "Institute code",
  name: "Institute name",
  admin_username: "Username",
  admin_email: "Email",
  admin_password: "Password",
  institute_code: "Institute code",
};

function fieldLabel(field: string) {
  return FIELD_LABELS[field] ?? genericLabel(field);
}

/** Names for nested groups; "" hides the group name (e.g. enrollment.roll_number -> "Roll number"). */
const GROUP_LABELS: Record<string, string> = { guardians: "Guardian", enrollment: "" };

function genericLabel(field: string) {
  return field.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());
}

/** "Guardian 2 Name" for ["guardians", 1, "name"]; top-level fields use FIELD_LABELS. */
function pathLabel(keys: (string | number)[]) {
  const parts: string[] = [];
  keys.forEach((key, i) => {
    if (typeof key === "number") {
      const group = GROUP_LABELS[String(keys[i - 1])] ?? "Item";
      parts.pop();
      parts.push(`${group} ${key + 1}`);
    } else if (key in GROUP_LABELS) {
      parts.push(GROUP_LABELS[key]);
    } else {
      parts.push(i === 0 ? fieldLabel(key) : genericLabel(key));
    }
  });
  return parts.filter(Boolean).join(" ");
}

/** Flatten DRF errors (possibly nested in objects and lists) into "Label: message" lines. */
function collect(value: unknown, keys: (string | number)[], out: string[]) {
  if (value === null || value === undefined) return;
  if (typeof value === "string") {
    const last = keys[keys.length - 1];
    const plain = last === undefined || last === "detail" || last === "non_field_errors";
    out.push(plain ? value : `${pathLabel(keys)}: ${value}`);
  } else if (Array.isArray(value)) {
    if (value.every((v) => typeof v === "string")) collect(value.join(" "), keys, out);
    else value.forEach((v, i) => collect(v, [...keys, i], out));
  } else if (typeof value === "object") {
    for (const [key, v] of Object.entries(value as Record<string, unknown>)) collect(v, [...keys, key], out);
  } else {
    out.push(String(value));
  }
}

/** Turn a DRF error response into readable lines. */
export function errorLines(err: unknown): string[] {
  if (err instanceof ApiError && err.body && typeof err.body === "object") {
    const out: string[] = [];
    collect(err.body, [], out);
    if (out.length) return out;
  }
  return [err instanceof Error ? err.message : "Something went wrong"];
}

export function ErrorBox({ error }: { error: unknown }) {
  if (!error) return null;
  return (
    <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
      {errorLines(error).map((line) => (
        <p key={line}>{line}</p>
      ))}
    </div>
  );
}
