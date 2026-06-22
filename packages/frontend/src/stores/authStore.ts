import { create } from "zustand";
import { login as apiLogin, register as apiRegister, refreshToken } from "../lib/authClient";

interface AuthState {
  user: { id: string; email: string } | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;

  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, browserId?: string) => Promise<void>;
  logout: () => void;
  refreshAuth: () => Promise<void>;
  hydrate: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  accessToken: null,
  refreshToken: null,
  isAuthenticated: false,

  login: async (email, password) => {
    const data = await apiLogin(email, password);
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    set({
      user: data.user,
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
      isAuthenticated: true,
    });
  },

  register: async (email, password, browserId) => {
    const data = await apiRegister(email, password, browserId);
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    set({
      user: data.user,
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
      isAuthenticated: true,
    });
  },

  logout: () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false });
  },

  refreshAuth: async () => {
    const rt = get().refreshToken || localStorage.getItem("refresh_token");
    if (!rt) return;
    try {
      const data = await refreshToken(rt);
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);
      set({
        user: data.user,
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        isAuthenticated: true,
      });
    } catch {
      get().logout();
    }
  },

  hydrate: () => {
    const rt = localStorage.getItem("refresh_token");
    if (rt) {
      const at = localStorage.getItem("access_token");
      set({ accessToken: at, refreshToken: rt });
      get().refreshAuth();
    }
  },
}));
