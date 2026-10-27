import type { Tenant } from "./api";

/** Default names for "Program" and "Section" by institute type. Institutes can override them. */
const DEFAULTS: Record<string, { program: string; section: string }> = {
  school: { program: "Class", section: "Section" },
  college: { program: "Class", section: "Section" },
  university: { program: "Program", section: "Section" },
  coaching: { program: "Course", section: "Batch" },
  tuition: { program: "Class", section: "Batch" },
};

export function pluralize(word: string) {
  if (/(s|x|z|ch|sh)$/i.test(word)) return `${word}es`;
  if (/[^aeiou]y$/i.test(word)) return `${word.slice(0, -1)}ies`;
  return `${word}s`;
}

export interface Terms {
  program: string;
  programs: string;
  section: string;
  sections: string;
}

export function termsFor(tenant: Tenant | null | undefined): Terms {
  const defaults = DEFAULTS[tenant?.institute_type ?? "school"] ?? DEFAULTS.school;
  const program = tenant?.program_label?.trim() || defaults.program;
  const section = tenant?.section_label?.trim() || defaults.section;
  return { program, programs: pluralize(program), section, sections: pluralize(section) };
}

export function defaultTermsFor(instituteType: string) {
  return DEFAULTS[instituteType] ?? DEFAULTS.school;
}

/** Example lists for the quick-add boxes. */
export const PROGRAM_EXAMPLES: Record<string, string[]> = {
  school: ["Nursery", "Prep", ...Array.from({ length: 10 }, (_, i) => `Class ${i + 1}`)],
  college: ["1st Year", "2nd Year"],
  university: ["BS Computer Science", "BBA", "BS English"],
  coaching: ["MDCAT Preparation", "ECAT Preparation", "IELTS"],
  tuition: Array.from({ length: 10 }, (_, i) => `Class ${i + 1}`),
};

export const SUBJECT_EXAMPLES = [
  "English",
  "Urdu",
  "Mathematics",
  "General Science",
  "Islamiyat",
  "Social Studies",
  "Computer Science",
];

/** Suggested name for the session that contains today, e.g. "2026-27". */
export function suggestedSession() {
  const now = new Date();
  // Most Pakistani schools start in April; use the calendar year otherwise.
  const startYear = now.getMonth() >= 3 ? now.getFullYear() : now.getFullYear() - 1;
  return {
    name: `${startYear}-${String(startYear + 1).slice(2)}`,
    start_date: `${startYear}-04-01`,
    end_date: `${startYear + 1}-03-31`,
  };
}
