import { apiClient, ApiResponse } from "./client";

export interface UserOut {
  id: string;
  email: string;
  full_name: string;
}

export const authApi = {
  register: (body: { email: string; password: string; full_name: string }) =>
    apiClient.post<ApiResponse<{ user_id: string }>>("/auth/register", body),

  login: (body: { email: string; password: string }) =>
    apiClient.post<ApiResponse<{ access_token: string; token_type: string }>>("/auth/login", body),

  me: () => apiClient.get<ApiResponse<UserOut>>("/auth/me"),
};
