import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { onSessionChanged, onUnauthorized, setCsrfToken } from "../services/api";
import {
  getCurrentUser,
  loginUser,
  logoutUser,
  type LoginCredentials,
  type User,
} from "../services/authService";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (credentials: LoginCredentials) => Promise<User>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUserState] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // Keep the in-memory CSRF token in sync with the signed-in user.
  const setUser = useCallback((next: User | null) => {
    setCsrfToken(next?.csrf_token ?? null, next?.id ?? null);
    setUserState(next);
  }, []);

  // Verify the existing session when the application starts.
  useEffect(() => {
    getCurrentUser()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, [setUser]);

  // Any 401 from the API (expired, revoked or suspended session) signs
  // the user out locally so protected routes redirect to login.
  useEffect(() => {
    onUnauthorized(() => setUser(null));
    return () => onUnauthorized(null);
  }, [setUser]);

  // Another account signed in from this browser (another tab): load it
  // so the page stops acting for the previous user.
  useEffect(() => {
    onSessionChanged(() => {
      getCurrentUser()
        .then(setUser)
        .catch(() => setUser(null));
    });
    return () => onSessionChanged(null);
  }, [setUser]);

  const login = useCallback(
    async (credentials: LoginCredentials): Promise<User> => {
      const authenticatedUser = await loginUser(credentials);
      setUser(authenticatedUser);
      return authenticatedUser;
    },
    [setUser]
  );

  const logout = useCallback(async (): Promise<void> => {
    try {
      await logoutUser();
    } finally {
      setUser(null);
    }
  }, [setUser]);

  const refreshUser = useCallback(async (): Promise<void> => {
    try {
      setUser(await getCurrentUser());
    } catch (error) {
      setUser(null);
      throw error;
    }
  }, [setUser]);

  const value = useMemo<AuthContextType>(
    () => ({ user, loading, isAuthenticated: user !== null, login, logout, refreshUser }),
    [user, loading, login, logout, refreshUser]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// Custom hook for accessing authentication.
// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used inside an AuthProvider.");
  }

  return context;
}
