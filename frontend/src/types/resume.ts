export interface Contact {
  location: string;
  email: string;
  phone: string;
  github: string; // schemeless, e.g. "github.com/x"
  linkedin: string; // schemeless
}

export interface ExperienceEntry {
  role: string;
  company: string;
  type: string;
  dates: string;
  highlights: string[];
}

// Also used for `capabilities` — items is a comma-joined STRING, not an array.
export interface SkillGroup {
  group: string;
  items: string;
}

export interface ImpactEntry {
  lead: string;
  text: string;
}

export interface LeadershipEntry {
  role: string;
  org: string;
  dates: string;
  description: string;
}

export interface EducationEntry {
  degree: string;
  school: string;
  year: string;
}

export const SECTION_KEYS = [
  "profile",
  "skills",
  "experience",
  "impact",
  "leadership",
  "education",
  "certifications",
  "capabilities",
  "career_progression",
  "professional_profile",
  "technology_index",
  "references",
] as const;

export type SectionKey = (typeof SECTION_KEYS)[number];

export const DEFAULT_SECTION_LABELS: Record<SectionKey, string> = {
  profile: "Profile",
  skills: "Core Technical Skills",
  experience: "Professional Experience",
  impact: "Selected Engineering Impact",
  leadership: "Leadership & Community",
  education: "Education",
  certifications: "Certifications & Professional Courses",
  capabilities: "Technical Capabilities",
  career_progression: "Career Progression",
  professional_profile: "Professional Profile",
  technology_index: "Selected Technology Index",
  references: "References",
};

export interface ResumeData {
  title: string;
  name: string;
  headline: string;
  contact: Contact;
  profile: string;
  skills: SkillGroup[];
  experience: ExperienceEntry[];
  impact: ImpactEntry[];
  leadership: LeadershipEntry[];
  education: EducationEntry[];
  certifications: string[]; // flat array of strings
  capabilities: SkillGroup[]; // same shape as skills
  career_progression: string;
  professional_profile: string;
  technology_index: string[]; // TRUE array (unlike skills[].items)
  references: string;
  section_labels: Partial<Record<SectionKey, string>>;
  sections: Partial<Record<SectionKey, boolean>>;
}

export function blankResumeData(): ResumeData {
  return {
    title: "",
    name: "",
    headline: "",
    contact: { location: "", email: "", phone: "", github: "", linkedin: "" },
    profile: "",
    skills: [],
    experience: [],
    impact: [],
    leadership: [],
    education: [],
    certifications: [],
    capabilities: [],
    career_progression: "",
    professional_profile: "",
    technology_index: [],
    references: "",
    section_labels: {},
    sections: {},
  };
}

export function resumeTitle(data: ResumeData): string {
  return data.title?.trim() || data.name?.trim() || "Untitled Resume";
}

export type ResumeSource = "built" | "uploaded";

export interface ResumeSummary {
  id: number;
  profile_id: number;
  name: string;
  template: string;
  font: string;
  source: ResumeSource;
  has_pdf: boolean;
  created_at: string;
  updated_at: string;
}

export interface Resume extends Omit<ResumeSummary, never> {
  data: ResumeData;
}

export interface Profile {
  id: number;
  user_id: number;
  name: string;
  headline: string | null;
  resume_count?: number;
  created_at: string;
  updated_at: string;
}

export interface User {
  id: number;
  email: string;
  created_at: string;
}

export type GenerationKind = "hr" | "ats" | "cover_letter";

export interface GenerationSummary {
  id: number;
  resume_id: number;
  kind: GenerationKind;
  job_description: string;
  created_at: string;
}

export interface Generation extends GenerationSummary {
  result: string;
}

export interface HistoryEntry extends GenerationSummary {
  resume_name: string;
  profile_id: number;
  profile_name: string;
  is_quick: boolean;
}

export interface TemplateMeta {
  label: string;
  description: string;
}

export interface FontMeta {
  label: string;
  available: boolean;
}

// --- Job board -----------------------------------------------------------

export type JobChannel = "email" | "whatsapp" | "telegram";

export interface JobSubscription {
  id: number;
  user_id: number;
  keyword: string;
  channel: JobChannel;
  channel_target: string;
  active: boolean;
  created_at: string;
}

export interface Job {
  id: number;
  source: string;
  title: string;
  company: string | null;
  location: string | null;
  job_type: string | null;
  salary: string | null;
  description: string | null;
  url: string;
  posted_at: string | null;
  fetched_at: string;
}

export interface JobNotification extends Job {
  notification_id: number;
  channel: JobChannel;
  status: string;
  sent_at: string;
}

export interface JobListResponse {
  items: Job[];
  total: number;
  page: number;
  page_size: number;
}

export interface JobFilterOptions {
  job_types: string[];
  sources: string[];
  locations: string[];
}
