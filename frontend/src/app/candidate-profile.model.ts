export interface CandidateProfile {
  id: number;
  full_name: string;
  headline: string;
  country: string;
  years_experience: number;
  english_level: string;
  created_at: string;
}

export type CandidateProfileCreate = Omit<CandidateProfile, 'id' | 'created_at'>;
