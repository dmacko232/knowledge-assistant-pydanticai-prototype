import { useState, useCallback } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { AuthContext, loadAuth, saveAuth, clearAuth } from "./auth";
import type { AuthUser } from "./types";
import Login from "./pages/Login";
import Chat from "./pages/Chat";

export default function App() {
  const [user, setUser] = useState<AuthUser | null>(loadAuth);

  const login = useCallback((u: AuthUser) => {
    saveAuth(u);
    setUser(u);
  }, []);

  const logout = useCallback(() => {
    clearAuth();
    setUser(null);
  }, []);

  return (
    <AuthContext value={{ user, login, logout }}>
      <Routes>
        <Route
          path="/login"
          element={user ? <Navigate to="/" replace /> : <Login />}
        />
        <Route
          path="/*"
          element={user ? <Chat /> : <Navigate to="/login" replace />}
        />
      </Routes>
    </AuthContext>
  );
}
