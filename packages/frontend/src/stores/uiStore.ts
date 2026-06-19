import { create } from "zustand";

interface UIState {
  loading: boolean;
  mobileMenuOpen: boolean;

  setLoading: (loading: boolean) => void;
  toggleMobileMenu: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  loading: false,
  mobileMenuOpen: false,

  setLoading: (loading) => set({ loading }),
  toggleMobileMenu: () => set((s) => ({ mobileMenuOpen: !s.mobileMenuOpen })),
}));
