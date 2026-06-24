import { create } from "zustand";
import { getProfile, submitOnboarding as apiSubmitOnboarding } from "../lib/apiClient";

export interface ProfileData {
  personality_tags: string[];
  emotion_tendency: Record<string, number>;
  preferred_accords: string[];
  preferred_notes: string[];
  gift_history: Array<{
    recipient: string;
    occasion: string;
    perfume: string;
  }>;
  profile_level: "light" | "full";
  questionnaire_completed: boolean;
  value_dimensions?: Record<string, number>;
}

interface ProfileState {
  profile: ProfileData | null;
  conversationCount: number;
  loading: boolean;
  error: string | null;
  valueDimensions: Record<string, number> | null;

  fetchProfile: () => Promise<void>;
  submitOnboarding: (answers: OnboardingAnswer[]) => Promise<void>;
  reset: () => void;
}

export interface OnboardingAnswer {
  question: number;
  option: string;
  mapped_vector: Record<string, number> | null;
  mapped_tags: string[] | null;
}

const initialState = {
  profile: null,
  conversationCount: 0,
  loading: false,
  error: null,
  valueDimensions: null,
};

export const useProfileStore = create<ProfileState>((set) => ({
  ...initialState,

  fetchProfile: async () => {
    set({ loading: true, error: null });
    try {
      const data = await getProfile();
      const profile = data.profile ? { ...(data.profile as unknown as ProfileData), value_dimensions: data.value_dimensions as Record<string, number> | undefined } : null;
      set({
        profile,
        conversationCount: data.conversation_count as number,
        valueDimensions: (data.value_dimensions as Record<string, number>) || null,
        loading: false,
      });
    } catch (e) {
      set({ error: "Failed to load profile", loading: false });
    }
  },

  submitOnboarding: async (answers: OnboardingAnswer[]) => {
    set({ loading: true, error: null });
    try {
      const data = await apiSubmitOnboarding(answers);
      set({
        profile: data.profile as unknown as ProfileData,
        loading: false,
      });
    } catch (e) {
      set({ error: "Failed to submit onboarding", loading: false });
    }
  },

  reset: () => set(initialState),
}));
