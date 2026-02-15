import { createContext, useContext } from "react";
import { logger } from "./logger";
import type { AuthUser } from "./types";

const log = logger("auth");
const STORAGE_KEY = "ka_auth";

export function saveAuth(user: AuthUser): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
  log.info("Auth saved", { userId: user.user_id, name: user.name });
}

export function loadAuth(): AuthUser | null {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    log.debug("No stored auth found");
    return null;
  }
  try {
    const user = JSON.parse(raw) as AuthUser;
    log.debug("Auth loaded from storage", { userId: user.user_id });
    return user;
  } catch {
    log.warn("Corrupt auth data in localStorage, clearing");
    localStorage.removeItem(STORAGE_KEY);
    return null;
  }
}

export function clearAuth(): void {
  localStorage.removeItem(STORAGE_KEY);
  log.info("Auth cleared (logout)");
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
