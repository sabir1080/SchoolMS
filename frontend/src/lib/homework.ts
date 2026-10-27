export interface Homework {
  id: number;
  section: number;
  section_name: string;
  subject: number | null;
  subject_name: string | null;
  date: string;
  due_date: string | null;
  title: string;
  details: string;
  created_by_name: string | null;
  can_edit: boolean;
}

/** Local date as YYYY-MM-DD (not UTC). */
export function isoDay(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export function shiftDay(iso: string, days: number) {
  const d = new Date(`${iso}T00:00:00`);
  d.setDate(d.getDate() + days);
  return isoDay(d);
}

export function dayTitle(iso: string) {
  return new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "short", year: "numeric" });
}
