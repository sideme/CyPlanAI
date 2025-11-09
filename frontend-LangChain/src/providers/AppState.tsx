"use client";

import {
  createContext,
  useContext,
  useMemo,
  useState,
  useEffect,
  type ReactNode,
  type Dispatch,
  type SetStateAction,
} from "react";

interface AppStateContextValue {
  threadId: string | null;
  setThreadId: Dispatch<SetStateAction<string | null>>;
  chatHistoryOpen: boolean;
  setChatHistoryOpen: Dispatch<SetStateAction<boolean>>;
  hideToolCalls: boolean;
  setHideToolCalls: Dispatch<SetStateAction<boolean>>;
  apiUrl: string;
  setApiUrl: Dispatch<SetStateAction<string>>;
  assistantId: string;
  setAssistantId: Dispatch<SetStateAction<string>>;
}

const AppStateContext = createContext<AppStateContextValue | undefined>(undefined);

function getDefaultApiUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:2024";
}

function getDefaultAssistantId(): string {
  return process.env.NEXT_PUBLIC_ASSISTANT_ID ?? "cyplanai";
}

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [threadId, setThreadId] = useState<string | null>(null);
  const [chatHistoryOpen, setChatHistoryOpen] = useState(false);
  const [hideToolCalls, setHideToolCalls] = useState(false);

  const [apiUrl, setApiUrl] = useState(getDefaultApiUrl);
  const [assistantId, setAssistantId] = useState(getDefaultAssistantId);

  useEffect(() => {
    if (typeof window === "undefined") return;

    if (window.location.search) {
      const newUrl = `${window.location.origin}${window.location.pathname}`;
      window.history.replaceState(null, "", newUrl);
    }

    const storedApiUrl = window.localStorage.getItem("cyplanai:apiUrl");
    const storedAssistantId = window.localStorage.getItem("cyplanai:assistantId");

    if (storedApiUrl) {
      setApiUrl(storedApiUrl);
    }
    if (storedAssistantId) {
      setAssistantId(storedAssistantId);
    }
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem("cyplanai:apiUrl", apiUrl);
  }, [apiUrl]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem("cyplanai:assistantId", assistantId);
  }, [assistantId]);

  const value = useMemo<AppStateContextValue>(
    () => ({
      threadId,
      setThreadId,
      chatHistoryOpen,
      setChatHistoryOpen,
      hideToolCalls,
      setHideToolCalls,
      apiUrl,
      setApiUrl,
      assistantId,
      setAssistantId,
    }),
    [
      threadId,
      chatHistoryOpen,
      hideToolCalls,
      apiUrl,
      assistantId,
    ],
  );

  return (
    <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>
  );
}

export function useAppState(): AppStateContextValue {
  const context = useContext(AppStateContext);
  if (context === undefined) {
    throw new Error("useAppState must be used within an AppStateProvider");
  }
  return context;
}
