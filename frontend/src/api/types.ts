import type { Role } from "../lib/nav";

export interface CentreLite {
  id: number;
  city: string;
  venue: string;
  date: string;
  slug: string;
  status: "planned" | "live" | "closed";
  opens_at: string;
  closes_at: string;
  front_desk_phone?: string;
}
export interface Warning {
  code: string;
  message: string;
}
export interface Envelope<T> {
  data: T;
  count?: number;
  total?: number;
  warnings?: Warning[];
  message?: string;
}

export interface Me {
  id: number;
  name: string;
  email: string;
  title: string;
  role: Role;
  counsellor: number | null;
  default_view: string;
  nav: { key: string; label: string }[];
  centre: CentreLite | null;
  posting: { id: number; desk_label: string; duty: string } | null;
}
export interface LoginResult {
  access: string;
  refresh: string;
  user: Me;
}

export interface PublicCentre {
  centre: CentreLite;
  open: boolean;
  message: string;
  stats: { waiting: number; counsellors_on_site: number; avg_wait_min: number | null; avg_wait_label: string };
  steps: string[];
  bring: string[];
  bring_note: string;
}
export type TokenState =
  | { kind: "waiting"; ahead: number; minutes: number; expected_at: string; approximate: boolean }
  | { kind: "next" }
  | { kind: "called" | "in_session"; recall_hold?: string }
  | { kind: "done" | "no_show" | "released" | "not_counselled" };
export interface TokenView {
  token: string;
  status: string;
  state: TokenState;
  stream: string;
  stream_name: string;
  name: string;
  mobile: string;
  counsellor: string;
  desk: string;
  venue: string;
  city: string;
  date: string;
  closes_at: string;
  front_desk_phone: string;
  checked_in_at: string;
  consent: "given" | "pending";
  rating: number | null;
  can_release: boolean;
  can_rate: boolean;
  centre_status: string;
  centre_slug: string;
}
export interface BoardPanel {
  desk: string;
  counsellor: string;
  duty: string;
  serving: string | null;
  next: string | null;
  waiting: number;
  line: string;
}
export interface Board {
  centre: CentreLite;
  now: string;
  total_waiting: number;
  panels: BoardPanel[];
  recently_called: string[];
  recently_called_empty: string;
  standing_line: string;
}

export interface StudentRecord {
  id: number;
  token: string;
  status: string;
  source: string;
  name: string;
  school: string;
  mobile: string;
  parent_mobile: string;
  email: string;
  stream: string;
  stream_name: string;
  klass: string;
  course: string;
  exams: string[];
  clarity: string;
  help: string[];
  consent: "given" | "pending";
  consent_at: string | null;
  consent_by: string | null;
  counsellor: { id: number; name: string; desk: string };
  checked_in_at: string;
  recalls: number;
  rating: number | null;
  outcome: string | null;
  follow_up_on: string | null;
  colleges_discussed: string;
  home_city: string;
  target_exam: string;
  budget: string;
  accompanied_by: string;
  notes: { id: number; text: string; author: string; at: string }[];
  timer: { elapsed_seconds: number; target_min: number; over_target: boolean; waiting: number } | null;
  audit?: { verb: string; at: string; actor: string; data: Record<string, unknown> }[];
  messages?: { id: number; template: string; status: string; at: string }[];
}
export interface HallRow {
  id: number;
  token: string;
  name: string;
  mobile: string;
  stream: string;
  status: string;
  source: string;
  counsellor: { id: number; name: string; desk: string };
  checked_in_at: string;
  waited_min: number | null;
  late: boolean;
  consent_pending: boolean;
  recalls: number;
  alert_failed: boolean;
  alert_failed_message: string;
}
export interface HallTab {
  key: string;
  label: string;
  counsellor_id: number | null;
  count: number;
  late: number;
  duty?: string;
}
export interface HallPayload {
  centre: CentreLite;
  header: { waiting: number; late: number; wait_promise_min: number };
  tabs: HallTab[];
  rows: HallRow[];
  query: string;
  count: number;
}
export interface DeskPayload {
  centre: CentreLite | null;
  message?: string;
  desk?: string;
  duty?: string;
  counsellor?: { id: number; name: string };
  figures?: {
    in_queue: number;
    waiting_hall: number;
    counselled_today: number;
    avg_session_min: number | null;
    target_session_min: number;
    late: number;
    wait_promise_min: number;
  };
  next_token?: string | null;
  current: StudentRecord | null;
  queue: {
    id: number;
    token: string;
    name: string;
    stream: string;
    klass: string;
    waited_min: number;
    source: string;
    consent_pending: boolean;
    late: boolean;
    next: boolean;
  }[];
  called?: string;
  warnings?: Warning[];
  message_text?: string;
}
export interface LiveCard {
  posting_id: number;
  counsellor_id: number;
  name: string;
  streams: string[];
  desk_label: string;
  duty: string;
  serving: { token: string; status: string } | null;
  queue_length: number;
  avg_session_min: number;
  counselled_today: number;
}
export interface LiveCentre extends CentreLite {
  counsellors: LiveCard[];
}
export interface CentreFull extends CentreLite {
  expected_students: number;
  covered_streams: string[];
  uncovered_streams: string[];
  counsellor_count: number;
}
export interface Posting {
  id: number;
  counsellor_id: number;
  centre_id: number;
  city: string;
  venue: string;
  date: string;
  centre_status: string;
  desk_label: string;
  duty: string;
}
export interface CounsellorFull {
  id: number;
  name: string;
  mobile: string;
  streams: string[];
  expected_session_min: number;
  postings: Posting[];
}
export interface OpsStudentRow {
  id: number;
  token: string;
  name: string;
  mobile: string;
  school: string;
  stream: string;
  course: string;
  centre: { id: number; city: string };
  date: string;
  counsellor: string;
  wait_min: number | null;
  session_min: number | null;
  outcome: string | null;
  status: string;
}
export interface Insights {
  headline: {
    counselled_or_queued: number;
    avg_wait: { value: number | null; n: number; label: string; promise_min: number };
    avg_session: { value: number | null; n: number; label: string; target_min: number };
    no_show_rate: { value: number | null; label: string; n: number };
  };
  demand: { stream: string; name: string; count: number; share: number }[];
  help: { option: string; count: number }[];
  clarity: { option: string; count: number }[];
  outcomes: { outcome: string | null; label: string; count: number }[];
  follow_ups: number;
  rating: { avg: number | null; n: number; label: string };
}
