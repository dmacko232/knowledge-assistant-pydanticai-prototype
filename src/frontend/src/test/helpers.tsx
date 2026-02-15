import { render, type RenderOptions } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AuthContext, type AuthContextValue } from "../auth";
import type { AuthUser } from "../types";
import type { ReactElement } from "react";

const MOCK_USER: AuthUser = {
  token: "test-jwt-token",
  user_id: "test-user-1",
  name: "Test User",
};

interface WrapperOptions {
  user?: AuthUser | null;
  route?: string;
}

export function renderWithProviders(
  ui: ReactElement,
  options: WrapperOptions & RenderOptions = {}
) {
  const { user = MOCK_USER, route = "/", ...renderOptions } = options;

  const authValue: AuthContextValue = {
    user,
    login: vi.fn(),
    logout: vi.fn(),
  };

  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <MemoryRouter initialEntries={[route]}>
        <AuthContext value={authValue}>{children}</AuthContext>
      </MemoryRouter>
    );
  }

  return { ...render(ui, { wrapper: Wrapper, ...renderOptions }), authValue };
}

export { MOCK_USER };
