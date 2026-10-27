export interface Period {
  id: number;
  name: string;
  start_time: string;
  end_time: string;
  is_break: boolean;
}

export interface Entry {
  id: number;
  section: number;
  section_name: string;
  day: number;
  period: number;
  subject: number | null;
  subject_name: string | null;
  teacher: number | null;
  teacher_name: string | null;
  room: string;
}

export interface Timetable {
  days: { day: number; name: string }[];
  periods: Period[];
  entries: Entry[];
  today: number;
  section?: { id: number; program_name: string; name: string; session_name: string };
}

export const DAY_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

/** "08:00:00" -> "8:00". */
export function hm(t: string) {
  const [h, m] = t.split(":");
  return `${Number(h)}:${m}`;
}
