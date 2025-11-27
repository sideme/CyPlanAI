"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { toast } from "sonner";

const TOKEN_STORAGE_KEY = "cyplanai:token";
const USER_STORAGE_KEY = "cyplanai:user";
const PREFERENCES_STORAGE_KEY = "cyplanai:preferences";
const LANGGRAPH_API_KEY_STORAGE_KEY = "lg:chat:apiKey";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8088";

export interface AuthUser {
  userId: string;
  username: string;
  email: string;
  role: string;
  name: string;
}

export interface UserPreferences {
  userId: string;
  theme: "light" | "dark";
  hideToolCalls: boolean;
  apiUrl: string | null;
  assistantId: string | null;
  sidebarOpen: boolean;
  updated_at: string | null;
}

interface AuthContextValue {
  user: AuthUser | null;
  token: string | null;
  backendUrl: string;
  loading: boolean;
  preferences: UserPreferences | null;
  login: (credentials: { username: string; password: string }) => Promise<void>;
  register: (payload: {
    username: string;
    password: string;
    email: string;
    name?: string;
  }) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  updatePreferences: (prefs: Partial<UserPreferences>) => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function persistAuth(
  token: string | null,
  user: AuthUser | null,
  preferences: UserPreferences | null
) {
  if (typeof window === "undefined") return;
  if (token) {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
    window.localStorage.setItem(LANGGRAPH_API_KEY_STORAGE_KEY, token);
  } else {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
    window.localStorage.removeItem(LANGGRAPH_API_KEY_STORAGE_KEY);
  }

  if (user) {
    window.localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
  } else {
    window.localStorage.removeItem(USER_STORAGE_KEY);
  }

  if (preferences) {
    window.localStorage.setItem(
      PREFERENCES_STORAGE_KEY,
      JSON.stringify(preferences)
    );
  } else {
    window.localStorage.removeItem(PREFERENCES_STORAGE_KEY);
  }
}

async function handleResponse(response: Response) {
  if (response.ok) {
    return response.json();
  }
  let message = "Unexpected error";
  try {
    const data = await response.json();
    message = data?.error ?? data?.message ?? message;
  } catch {
    // ignore json parsing error
  }
  throw new Error(message);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [preferences, setPreferences] = useState<UserPreferences | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchCurrentUser = useCallback(async (authToken: string) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/auth/me`, {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      });
      const data = await handleResponse(response);
      const { preferences: prefs, ...userData } = data;
      setUser(userData);
      setToken(authToken);
      setPreferences(prefs || null);
      persistAuth(authToken, userData, prefs || null);
    } catch (error) {
      console.error("Failed to fetch current user", error);
      setUser(null);
      setToken(null);
      setPreferences(null);
      persistAuth(null, null, null);
      throw error;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const storedToken = window.localStorage.getItem(TOKEN_STORAGE_KEY);
    const storedUser = window.localStorage.getItem(USER_STORAGE_KEY);
    const storedPrefs = window.localStorage.getItem(PREFERENCES_STORAGE_KEY);

    if (storedToken) {
      setToken(storedToken);
      if (storedUser) {
        try {
          const parsedUser = JSON.parse(storedUser) as AuthUser;
          setUser(parsedUser);
        } catch {
          // ignore parse errors and refetch below
        }
      }
      if (storedPrefs) {
        try {
          const parsedPrefs = JSON.parse(storedPrefs) as UserPreferences;
          setPreferences(parsedPrefs);
        } catch {
          // ignore parse errors
        }
      }
      fetchCurrentUser(storedToken).catch(() => undefined);
    } else {
      setLoading(false);
    }
  }, [fetchCurrentUser]);

  const login = useCallback(
    async ({ username, password }: { username: string; password: string }) => {
      const response = await fetch(`${BACKEND_URL}/api/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ username, password }),
      });
      const data = await handleResponse(response);
      const accessToken = data?.access_token as string | undefined;
      const userData = data?.user as AuthUser | undefined;
      const prefsData = data?.preferences as UserPreferences | undefined;
      if (!accessToken || !userData) {
        throw new Error("Login response was missing required fields");
      }
      setUser(userData);
      setToken(accessToken);
      setPreferences(prefsData || null);
      persistAuth(accessToken, userData, prefsData || null);
      toast.success("Signed in successfully");
    },
    []
  );

  const register = useCallback(
    async ({
      username,
      password,
      email,
      name,
    }: {
      username: string;
      password: string;
      email: string;
      name?: string;
    }) => {
      const response = await fetch(`${BACKEND_URL}/api/auth/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ username, password, email, name }),
      });
      const data = await handleResponse(response);
      const accessToken = data?.access_token as string | undefined;
      const userData = data?.user as AuthUser | undefined;
      const prefsData = data?.preferences as UserPreferences | undefined;
      if (!accessToken || !userData) {
        throw new Error("Registration response was missing required fields");
      }
      setUser(userData);
      setToken(accessToken);
      setPreferences(prefsData || null);
      persistAuth(accessToken, userData, prefsData || null);
      toast.success("Account created successfully");
    },
    []
  );

  const logout = useCallback(() => {
    setUser(null);
    setToken(null);
    setPreferences(null);
    persistAuth(null, null, null);
  }, []);

  const refreshUser = useCallback(async () => {
    if (!token) return;
    await fetchCurrentUser(token);
  }, [fetchCurrentUser, token]);

  const updatePreferences = useCallback(
    async (prefs: Partial<UserPreferences>) => {
      if (!token) {
        throw new Error("Not authenticated");
      }

      const response = await fetch(`${BACKEND_URL}/api/preferences/`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(prefs),
      });

      const data = await handleResponse(response);
      const updatedPrefs = data?.preferences as UserPreferences | undefined;

      if (updatedPrefs) {
        setPreferences(updatedPrefs);
        // Also update localStorage
        window.localStorage.setItem(
          PREFERENCES_STORAGE_KEY,
          JSON.stringify(updatedPrefs)
        );
      }
    },
    [token]
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      token,
      backendUrl: BACKEND_URL,
      loading,
      preferences,
      login,
      register,
      logout,
      refreshUser,
      updatePreferences,
    }),
    [
      user,
      token,
      loading,
      preferences,
      login,
      register,
      logout,
      refreshUser,
      updatePreferences,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

