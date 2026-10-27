export interface AcademicSession {
  id: number;
  name: string;
  start_date: string;
  end_date: string;
  is_current: boolean;
}

export interface Subject {
  id: number;
  name: string;
  code: string;
  is_active: boolean;
}

export interface Program {
  id: number;
  name: string;
  code: string;
  description: string;
  sort_order: number;
  is_active: boolean;
  subjects: number[];
  section_count: number;
}

export interface Section {
  id: number;
  program: number;
  program_name: string;
  session: number;
  session_name: string;
  name: string;
  capacity: number | null;
  class_teacher: number | null;
  class_teacher_name: string | null;
  is_active: boolean;
}
