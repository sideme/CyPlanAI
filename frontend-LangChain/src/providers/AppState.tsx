"use client";

import {
  createContext,
  useContext,
  useMemo,
  useState,
  useEffect,
  useCallback,
  useRef,
  type ReactNode,
  type Dispatch,
  type SetStateAction,
} from "react";
import { useAuth } from "./Auth";

interface AppStateContextValue {
  threadId: string | null;
  setThreadId: Dispatch<SetStateAction<string | null>>;
  chatHistoryOpen: boolean;
  setChatHistoryOpen: Dispatch<SetStateAction<boolean>>;
  settingsOpen: boolean;
  setSettingsOpen: Dispatch<SetStateAction<boolean>>;
  searchOpen: boolean;
  setSearchOpen: Dispatch<SetStateAction<boolean>>;
  theme: "light" | "dark";
  setTheme: Dispatch<SetStateAction<"light" | "dark">>;
  hideToolCalls: boolean;
  setHideToolCalls: Dispatch<SetStateAction<boolean>>;
  apiUrl: string;
  setApiUrl: Dispatch<SetStateAction<string>>;
  assistantId: string;
  setAssistantId: Dispatch<SetStateAction<string>>;
  syncPreferences: () => Promise<void>;
}

const AppStateContext = createContext<AppStateContextValue | undefined>(
  undefined
);

export function getDefaultApiUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:2024";
}

export function getDefaultAssistantId(): string {
  return process.env.NEXT_PUBLIC_ASSISTANT_ID ?? "cyplanai";
}

export function AppStateProvider({ children }: { children: ReactNode }) {
  const { preferences, updatePreferences, user } = useAuth();
  const [threadId, setThreadId] = useState<string | null>(null);
  const [chatHistoryOpen, setChatHistoryOpen] = useState(true);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [theme, setTheme] = useState<"light" | "dark">("dark");
  const [hideToolCalls, setHideToolCalls] = useState(true);
  const [apiUrl, setApiUrl] = useState(getDefaultApiUrl);
  const [assistantId, setAssistantId] = useState(getDefaultAssistantId);

  // Track if we've initialized from server preferences
  const initializedFromServer = useRef(false);

  // Initialize from localStorage first (for quick load)
  useEffect(() => {
    if (typeof window === "undefined") return;

    if (window.location.search) {
      const newUrl = `${window.location.origin}${window.location.pathname}`;
      window.history.replaceState(null, "", newUrl);
    }

    // Load from localStorage as initial values
    const storedTheme = window.localStorage.getItem("cyplanai:theme");
    if (storedTheme === "light" || storedTheme === "dark") {
      setTheme(storedTheme);
    } else {
      const prefersDark = window.matchMedia(
        "(prefers-color-scheme: dark)"
      ).matches;
      setTheme(prefersDark ? "dark" : "light");
    }

    const storedApiUrl = window.localStorage.getItem("cyplanai:apiUrl");
    const storedAssistantId = window.localStorage.getItem(
      "cyplanai:assistantId"
    );
    const storedHideToolCalls = window.localStorage.getItem(
      "cyplanai:hideToolCalls"
    );
    const storedSidebarOpen = window.localStorage.getItem(
      "cyplanai:sidebarOpen"
    );

    if (storedApiUrl) setApiUrl(storedApiUrl);
    if (storedAssistantId) setAssistantId(storedAssistantId);
    if (storedHideToolCalls === "true") {
      setHideToolCalls(true);
    } else if (storedHideToolCalls === "false") {
      setHideToolCalls(false);
    }
    if (storedSidebarOpen === "false") setChatHistoryOpen(false);
  }, []);

  // Sync from server preferences when user logs in
  useEffect(() => {
    if (!preferences || !user || initializedFromServer.current) return;

    // Override with server preferences
    if (preferences.theme) {
      setTheme(preferences.theme);
    }
    if (preferences.hideToolCalls !== undefined) {
      setHideToolCalls(preferences.hideToolCalls);
    }
    if (preferences.apiUrl) {
      setApiUrl(preferences.apiUrl);
    }
    if (preferences.assistantId) {
      setAssistantId(preferences.assistantId);
    }
    if (preferences.sidebarOpen !== undefined) {
      // Only apply on desktop
      if (typeof window !== "undefined" && window.innerWidth >= 1024) {
        setChatHistoryOpen(preferences.sidebarOpen);
      }
    }

    initializedFromServer.current = true;
  }, [preferences, user]);

  // Reset initialization flag when user logs out
  useEffect(() => {
    if (!user) {
      initializedFromServer.current = false;
    }
  }, [user]);

  // Collapse sidebar on narrow screens
  useEffect(() => {
    if (typeof window === "undefined") return;
    const prefersNarrow = window.innerWidth < 1024;
    if (prefersNarrow) {
      setChatHistoryOpen(false);
    }
  }, []);

  // Persist to localStorage when values change
  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem("cyplanai:apiUrl", apiUrl);
  }, [apiUrl]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem("cyplanai:assistantId", assistantId);
  }, [assistantId]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    document.documentElement.classList.remove("light", "dark");
    document.documentElement.classList.add(theme);
    window.localStorage.setItem("cyplanai:theme", theme);
  }, [theme]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(
      "cyplanai:hideToolCalls",
      hideToolCalls.toString()
    );
  }, [hideToolCalls]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(
      "cyplanai:sidebarOpen",
      chatHistoryOpen.toString()
    );
  }, [chatHistoryOpen]);

  // Function to sync current state to backend
  const syncPreferences = useCallback(async () => {
    if (!user) return;

    try {
      await updatePreferences({
        theme,
        hideToolCalls,
        apiUrl: apiUrl !== getDefaultApiUrl() ? apiUrl : null,
        assistantId:
          assistantId !== getDefaultAssistantId() ? assistantId : null,
        sidebarOpen: chatHistoryOpen,
      });
    } catch (error) {
      console.error("Failed to sync preferences:", error);
    }
  }, [
    user,
    updatePreferences,
    theme,
    hideToolCalls,
    apiUrl,
    assistantId,
    chatHistoryOpen,
  ]);

  const value = useMemo<AppStateContextValue>(
    () => ({
      threadId,
      setThreadId,
      chatHistoryOpen,
      setChatHistoryOpen,
      settingsOpen,
      setSettingsOpen,
      searchOpen,
      setSearchOpen,
      theme,
      setTheme,
      hideToolCalls,
      setHideToolCalls,
      apiUrl,
      setApiUrl,
      assistantId,
      setAssistantId,
      syncPreferences,
    }),
    [
      threadId,
      chatHistoryOpen,
      settingsOpen,
      searchOpen,
      theme,
      hideToolCalls,
      apiUrl,
      assistantId,
      syncPreferences,
    ]
  );

  return (
    <AppStateContext.Provider value={value}>
      {children}
    </AppStateContext.Provider>
  );
}

export function useAppState(): AppStateContextValue {
  const context = useContext(AppStateContext);
  if (context === undefined) {
    throw new Error("useAppState must be used within an AppStateProvider");
  }
  return context;
}
