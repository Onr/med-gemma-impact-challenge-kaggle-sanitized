export enum Phase {
  ASK = 'ASK',
  ACQUIRE = 'ACQUIRE',
  APPRAISE = 'APPRAISE',
  APPLY = 'APPLY',
  ASSESS = 'ASSESS'
}

export enum Role {
  PHYSICIAN = 'Physician',
  PT = 'Physical Therapist',
  OT = 'Occupational Therapist',
  NURSE = 'Nurse',
  PHARMACIST = 'Pharmacist'
}

export interface MessageImage {
  mimeType: string;
  data: string; // base64
  preview?: string; // URL for display
}

export interface Message {
  id: string;
  role: 'user' | 'model';
  content: string;
  timestamp: number;
  phase?: Phase; // Track which phase this message belongs to
  extractedData?: any;
  images?: MessageImage[]; // Attached images for multimodal
}

export interface PicoData {
  patient: string;
  intervention: string;
  comparison: string;
  outcome: string;
  completeness: number; // 0-100
}

export interface Reference {
  id: string;
  title: string;
  source: string;
  year: string;
  type: string;
  relevance: 'High' | 'Medium' | 'Low';
  timestamp?: number;
  // PubMed integration
  pubmedId?: string;
  url?: string;
}

export interface AppraisalPoint {
  id: string;
  title: string;
  description: string;
  verdict: 'Positive' | 'Negative' | 'Neutral';
  timestamp?: number;
}

export interface ApplyPoint {
  id: string;
  action: string;
  rationale: string;
  timestamp?: number;
}

export interface AssessPoint {
  id: string;
  metric: string;
  target: string;
  frequency: string;
  timestamp?: number;
}

// Available MedGemma model options
export type ModelKey =
  | 'medgemma-4b-it'
  | 'medgemma-27b-text'
  | 'medgemma-27b-mm'
  | 'gemini-flash';

export interface AppState {
  currentPhase: Phase;
  userRole: Role;
  patientContext: string;
  pico: PicoData;
  references: Reference[];
  appraisals: AppraisalPoint[];
  applyPoints: ApplyPoint[];
  assessPoints: AssessPoint[];
  messages: Message[];
  isLoading: boolean;
  // Model configuration
  selectedModel: ModelKey;
}
