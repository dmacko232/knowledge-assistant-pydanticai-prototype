import { createContext, useContext } from "react";
import type { AuthUser } from "./types";

const STORAGE_KEY = "ka_auth";

export function saveAuth(user: AuthUser): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
}

export function loadAuth(): AuthUser | null {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function clearAuth(): void {
  localStorage.removeItem(STORAGE_KEY);
}

export interface AuthContextValue {
  user: AuthUser | null;
  login: (user: AuthUser) => void;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextValue>({
  user: null,
  login: () => {},
  logout: () => {},
});

export function useAuth(): AuthContextValue {
  return useContext(AuthContext);
}
