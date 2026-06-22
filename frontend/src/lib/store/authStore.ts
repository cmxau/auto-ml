import { create } from "zustand";
import { persist } from "zustand/middleware";

interface User {
  id: string;
  email: string;
  full_name: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  setAuth: (user: User, token: string) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      setAuth: (user, token) => {
        localStorage.setItem("access_token", token);
        set({ user, token });
      },
      clearAuth: () => {
        localStorage.removeItem("access_token");
        set({ user: null, token: null });
      },
    }),
    { name: "auth-store" }
  )
);
