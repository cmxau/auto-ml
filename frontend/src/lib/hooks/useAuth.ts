"use client";
import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { authApi } from "../api/auth";
import { useAuthStore } from "../store/authStore";

function setAuthCookie(token: string) {
  document.cookie = `access_token=${token}; path=/; max-age=${60 * 60 * 24}; SameSite=Lax`;
}

function clearAuthCookie() {
  document.cookie = "access_token=; path=/; max-age=0";
}

export function useLogin() {
  const setAuth = useAuthStore((s) => s.setAuth);
  const router = useRouter();
  return useMutation({
    mutationFn: async (data: { email: string; password: string }) => {
      const loginRes = await authApi.login(data);
      const token = loginRes.data.data.access_token;
      // Temporarily set token so the /me request is authenticated
      localStorage.setItem("access_token", token);
      try {
        const meRes = await authApi.me();
        return { user: meRes.data.data, token };
      } catch (err) {
        // Clean up if /me fails — don't leave a dangling token
        localStorage.removeItem("access_token");
        throw err;
      }
    },
    onSuccess: ({ user, token }) => {
      setAuth(user, token); // setAuth also writes to localStorage (idempotent)
      setAuthCookie(token);
      router.push("/dashboard");
    },
  });
}

export function useRegister() {
  const router = useRouter();
  return useMutation({
    mutationFn: (data: { email: string; password: string; full_name: string }) =>
      authApi.register(data),
    onSuccess: () => router.push("/login"),
  });
}

export function useLogout() {
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const router = useRouter();
  return () => {
    clearAuth();
    clearAuthCookie();
    router.push("/login");
  };
}
