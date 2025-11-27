import { validate } from "uuid";
import { getApiKey } from "@/lib/api-key";
import { Thread } from "@langchain/langgraph-sdk";
import {
  createContext,
  useContext,
  ReactNode,
  useCallback,
  useState,
  Dispatch,
  SetStateAction,
} from "react";
import { createClient } from "./client";
import { useAppState } from "./AppState";
import { useAuth } from "./Auth";

interface ThreadContextType {
  getThreads: () => Promise<Thread[]>;
  threads: Thread[];
  setThreads: Dispatch<SetStateAction<Thread[]>>;
  threadsLoading: boolean;
  setThreadsLoading: Dispatch<SetStateAction<boolean>>;
  renameThread: (threadId: string, title: string | null) => Promise<void>;
}

const ThreadContext = createContext<ThreadContextType | undefined>(undefined);

function getThreadSearchMetadata(
  assistantId: string,
): { graph_id: string } | { assistant_id: string } {
  if (validate(assistantId)) {
    return { assistant_id: assistantId };
  } else {
    return { graph_id: assistantId };
  }
}

export function ThreadProvider({ children }: { children: ReactNode }) {
  const { apiUrl, assistantId } = useAppState();
  const { token } = useAuth();
  const [threads, setThreads] = useState<Thread[]>([]);
  const [threadsLoading, setThreadsLoading] = useState(false);

  const getThreads = useCallback(async (): Promise<Thread[]> => {
    if (!apiUrl || !assistantId) return [];
    const authToken = token ?? getApiKey() ?? undefined;
    const client = createClient(apiUrl, authToken);

    const threads = await client.threads.search({
      metadata: {
        ...getThreadSearchMetadata(assistantId),
      },
      limit: 100,
    });

    return threads;
  }, [apiUrl, assistantId, token]);

  const renameThread = useCallback(
    async (threadId: string, title: string | null) => {
      if (!apiUrl || !token) {
        throw new Error("Missing API configuration or authentication");
      }
      const response = await fetch(`${apiUrl}/threads/${threadId}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ title }),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        const message =
          payload?.error ?? payload?.message ?? "Failed to update thread title";
        throw new Error(message);
      }
      const data = (await response.json()) as {
        metadata?: Record<string, unknown>;
      };
      setThreads((prev) =>
        prev.map((thread) =>
          thread.thread_id === threadId
            ? {
                ...thread,
                metadata: {
                  ...(thread.metadata ?? {}),
                  ...(data.metadata ?? {}),
                },
              }
            : thread,
        ),
      );
    },
    [apiUrl, token],
  );

  const value = {
    getThreads,
    threads,
    setThreads,
    threadsLoading,
    setThreadsLoading,
    renameThread,
  };

  return (
    <ThreadContext.Provider value={value}>{children}</ThreadContext.Provider>
  );
}

export function useThreads() {
  const context = useContext(ThreadContext);
  if (context === undefined) {
    throw new Error("useThreads must be used within a ThreadProvider");
  }
  return context;
}
