import React, {
  createContext,
  useContext,
  ReactNode,
  useState,
  useEffect,
  useRef,
} from "react";
import { useStream } from "@langchain/langgraph-sdk/react";
import type { StreamMessage } from "@/types/langgraph";
import {
  uiMessageReducer,
  isUIMessage,
  isRemoveUIMessage,
  type UIMessage,
  type RemoveUIMessage,
} from "@langchain/langgraph-sdk/react-ui";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { LangGraphLogoSVG } from "@/components/icons/langgraph";
import { Label } from "@/components/ui/label";
import { ArrowRight } from "lucide-react";
import { PasswordInput } from "@/components/ui/password-input";
import { getApiKey } from "@/lib/api-key";
import { useThreads } from "./Thread";
import { toast } from "sonner";
import { useAppState } from "./AppState";

export type StateType = { messages: StreamMessage[]; ui?: UIMessage[] };

const useTypedStream = useStream<
  StateType,
  {
    UpdateType: {
      messages?: StreamMessage[] | StreamMessage | string;
      ui?: (UIMessage | RemoveUIMessage)[] | UIMessage | RemoveUIMessage;
      context?: Record<string, unknown>;
    };
    CustomEventType: UIMessage | RemoveUIMessage;
  }
>;

type StreamContextType = ReturnType<typeof useTypedStream>;
const StreamContext = createContext<StreamContextType | undefined>(undefined);

async function sleep(ms = 4000) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function checkGraphStatus(
  apiUrl: string,
  apiKey: string | null,
): Promise<boolean> {
  try {
    const res = await fetch(`${apiUrl}/info`, {
      ...(apiKey && {
        headers: {
          "X-Api-Key": apiKey,
        },
      }),
    });

    return res.ok;
  } catch (e) {
    return false;
  }
}

// Custom state to store messages directly from SSE (bypassing SDK's stream.values)
const DirectSSEContext = createContext<{
  messages: StreamMessage[];
  setMessages: React.Dispatch<React.SetStateAction<StreamMessage[]>>;
  addOptimisticMessage: (message: StreamMessage) => void;
  apiUrl: string;
  apiKey: string | null;
  assistantId: string;
} | undefined>(undefined);

const getMessageSignature = (message: StreamMessage): string => {
  const type = message?.type ?? "";
  const content = Array.isArray(message?.content)
    ? JSON.stringify(message.content)
    : typeof message?.content === "string"
      ? message.content
      : JSON.stringify(message?.content ?? "");
  return `${type}:${content}`;
};

const StreamSession = ({
  children,
  apiKey,
}: {
  children: ReactNode;
  apiKey: string | null;
}) => {
  const {
    threadId,
    setThreadId,
    apiUrl,
    assistantId,
  } = useAppState();
  const { getThreads, setThreads } = useThreads();
  
  // Custom state to store messages directly from SSE
  const [directSSEMessages, setDirectSSEMessages] = useState<StreamMessage[]>([]);
  const directSSEMessagesRef = useRef<StreamMessage[]>([]);
  useEffect(() => {
    directSSEMessagesRef.current = directSSEMessages;
  }, [directSSEMessages]);
  
  const streamValue = useTypedStream({
    apiUrl,
    apiKey: apiKey ?? undefined,
    assistantId,
    threadId: threadId ?? null,
    fetchStateHistory: false,
    onCustomEvent: (
      event: UIMessage | RemoveUIMessage,
      options: { mutate: (updater: (prev: StateType) => StateType) => void },
    ) => {
      if (isUIMessage(event) || isRemoveUIMessage(event)) {
        options.mutate((prev: StateType) => {
          const ui = uiMessageReducer(prev.ui ?? [], event);
          return { ...prev, ui };
        });
      }
    },
    onUpdateEvent: (data: Record<string, unknown>) => {
      const nextMessages = [...directSSEMessagesRef.current];
      Object.values(data ?? {}).forEach((update: any) => {
        if (!update) return;
        const maybeMessages = Array.isArray(update)
          ? update
          : update.messages ?? update?.values?.messages ?? [];
        if (Array.isArray(maybeMessages)) {
          maybeMessages.forEach((msg: StreamMessage) => {
            if (!msg || typeof msg !== "object") return;
            const signature = getMessageSignature(msg as StreamMessage);
            const optimisticIndex = nextMessages.findIndex(
              (m) => Boolean(m?.clientOptimistic) && getMessageSignature(m) === signature,
            );

            if (optimisticIndex !== -1) {
              const existingMessage = nextMessages[optimisticIndex];
              const resolvedId = (msg.id ?? existingMessage.id ?? crypto.randomUUID()) as string;
              nextMessages[optimisticIndex] = {
                ...existingMessage,
                ...msg,
                id: resolvedId,
                clientOptimistic: false,
              };
              return;
            }

            const id: string = msg.id ?? crypto.randomUUID();
            const existingIndex = nextMessages.findIndex((m) => (m.id ?? "") === id);
            if (existingIndex >= 0) {
              nextMessages[existingIndex] = {
                ...nextMessages[existingIndex],
                ...msg,
                clientOptimistic: false,
              };
              return;
            }

            nextMessages.push({ ...msg, id, clientOptimistic: false });
          });
        }
      });
      if (nextMessages.length > 0) {
        setDirectSSEMessages(nextMessages);
      }
    },
    onThreadId: (id: string | null) => {
      setThreadId(id);
      // Refetch threads list when thread ID changes.
      // Wait for some seconds before fetching so we're able to get the new thread that was created.
      sleep().then(() => getThreads().then(setThreads).catch(() => undefined));
    },
  });
  
  // Intercept SSE events and manually update directSSEMessages
  // This bypasses SDK's stream.values update mechanism
  // We monitor both stream.values and stream.messages to catch any updates
  useEffect(() => {
    const currentValues = streamValue.values;
    const currentMessages = streamValue.messages || [];
 
    if (currentValues?.messages && Array.isArray(currentValues.messages)) {
      const incomingMessages = currentValues.messages as StreamMessage[];
      const existingMessages = directSSEMessagesRef.current;
      const matchedOptimisticIndexes = new Set<number>();

      const normalizedIncoming = incomingMessages.map((msg: StreamMessage) => {
        const signature = getMessageSignature(msg);
        const optimisticIndex = existingMessages.findIndex((existing, idx) => {
          if (matchedOptimisticIndexes.has(idx)) return false;
          return Boolean(existing?.clientOptimistic) && getMessageSignature(existing) === signature;
        });

        if (optimisticIndex !== -1) {
          matchedOptimisticIndexes.add(optimisticIndex);
          const optimisticMessage = existingMessages[optimisticIndex];
          return {
            ...optimisticMessage,
            ...msg,
            id: msg.id ?? optimisticMessage.id ?? crypto.randomUUID(),
            clientOptimistic: false,
          };
        }

        return {
          ...msg,
          id: msg.id ?? crypto.randomUUID(),
          clientOptimistic: false,
        };
      });

      const preservedExisting = existingMessages.filter((_, idx) => !matchedOptimisticIndexes.has(idx));

      setDirectSSEMessages([...preservedExisting, ...normalizedIncoming]);
    } else if (currentMessages.length > 0 && directSSEMessagesRef.current.length === 0) {
      setDirectSSEMessages(currentMessages as StreamMessage[]);
    }
  }, [streamValue.values, streamValue.messages]);

  const addOptimisticMessage = (message: StreamMessage) => {
    setDirectSSEMessages((prev) => [...prev, { ...message, clientOptimistic: true }]);
  };

  // Track previous message counts and IDs to detect actual changes
  const prevValuesCountRef = useRef(0);
  const prevStreamCountRef = useRef(0);
  const prevValuesIdsRef = useRef<string[]>([]);
  
  // Log every time values.messages changes (to catch all SSE events)
  useEffect(() => {
    const valuesMessages = streamValue.values?.messages || [];
    const streamMessages = streamValue.messages || [];
    
    const valuesCount = valuesMessages.length;
    const streamCount = streamMessages.length;
    const valuesIds = valuesMessages.map((m: any) => m?.id || '').filter(Boolean);
    
    // Check if values actually changed (count or IDs)
    const valuesChanged = 
      valuesCount !== prevValuesCountRef.current ||
      JSON.stringify(valuesIds) !== JSON.stringify(prevValuesIdsRef.current);
    
    if (valuesChanged) {
      prevValuesCountRef.current = valuesCount;
      prevStreamCountRef.current = streamCount;
      prevValuesIdsRef.current = valuesIds;
    }
  }, [streamValue.values, streamValue.messages, streamValue.isLoading]);

  useEffect(() => {
    checkGraphStatus(apiUrl, apiKey).then((ok) => {
      if (!ok) {
        toast.error("Failed to connect to LangGraph server", {
          description: () => (
            <p>
              Please ensure your graph is running at <code>{apiUrl}</code> and
              your API key is correctly set (if connecting to a deployed graph).
            </p>
          ),
          duration: 10000,
          richColors: true,
          closeButton: true,
        });
      }
    });
  }, [apiKey, apiUrl]);

  return (
    <StreamContext.Provider value={streamValue}>
      <DirectSSEContext.Provider
        value={{
          messages: directSSEMessages,
          setMessages: setDirectSSEMessages,
          addOptimisticMessage,
          apiUrl,
          apiKey,
          assistantId,
        }}
      >
        {children}
      </DirectSSEContext.Provider>
    </StreamContext.Provider>
  );
};

// Default values for the form
const DEFAULT_API_URL = "http://localhost:2024";
const DEFAULT_ASSISTANT_ID = "cyplanai";

export const StreamProvider: React.FC<{ children: ReactNode }> = ({
  children,
}) => {
  const {
    apiUrl,
    setApiUrl,
    assistantId,
    setAssistantId,
  } = useAppState();

  // For API key, use localStorage with env var fallback
  const [apiKey, _setApiKey] = useState(() => {
    const storedKey = getApiKey();
    return storedKey || "";
  });

  const setApiKey = (key: string) => {
    window.localStorage.setItem("lg:chat:apiKey", key);
    _setApiKey(key);
  };

  // Determine final values to use, prioritizing URL params then env vars then defaults
  const finalApiUrl = apiUrl || DEFAULT_API_URL;
  const finalAssistantId = assistantId || DEFAULT_ASSISTANT_ID;

  // Show the form if we: don't have an API URL, or don't have an assistant ID
  // (This should rarely happen now with defaults)
  if (!finalApiUrl || !finalAssistantId) {
    return (
      <div className="flex min-h-screen w-full items-center justify-center p-4">
        <div className="animate-in fade-in-0 zoom-in-95 bg-background flex max-w-3xl flex-col rounded-lg border shadow-lg">
          <div className="mt-14 flex flex-col gap-2 border-b p-6">
            <div className="flex flex-col items-start gap-2">
              <LangGraphLogoSVG className="h-7" />
              <h1 className="text-xl font-semibold tracking-tight">
                Agent Chat
              </h1>
            </div>
            <p className="text-muted-foreground">
              Welcome to Agent Chat! Before you get started, you need to enter
              the URL of the deployment and the assistant / graph ID.
            </p>
          </div>
          <form
            onSubmit={(e) => {
              e.preventDefault();

              const form = e.target as HTMLFormElement;
              const formData = new FormData(form);
              const apiUrl = formData.get("apiUrl") as string;
              const assistantId = formData.get("assistantId") as string;
              const apiKey = formData.get("apiKey") as string;

              setApiUrl(apiUrl);
              setApiKey(apiKey);
              setAssistantId(assistantId);

              form.reset();
            }}
            className="bg-muted/50 flex flex-col gap-6 p-6"
          >
            <div className="flex flex-col gap-2">
              <Label htmlFor="apiUrl">
                Deployment URL<span className="text-rose-500">*</span>
              </Label>
              <p className="text-muted-foreground text-sm">
                This is the URL of your LangGraph deployment. Can be a local, or
                production deployment.
              </p>
              <Input
                id="apiUrl"
                name="apiUrl"
                className="bg-background"
                defaultValue={apiUrl || DEFAULT_API_URL}
                required
              />
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="assistantId">
                Assistant / Graph ID<span className="text-rose-500">*</span>
              </Label>
              <p className="text-muted-foreground text-sm">
                This is the ID of the graph (can be the graph name), or
                assistant to fetch threads from, and invoke when actions are
                taken.
              </p>
              <Input
                id="assistantId"
                name="assistantId"
                className="bg-background"
                defaultValue={assistantId || DEFAULT_ASSISTANT_ID}
                required
              />
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="apiKey">LangSmith API Key</Label>
              <p className="text-muted-foreground text-sm">
                This is <strong>NOT</strong> required if using a local LangGraph
                server. This value is stored in your browser's local storage and
                is only used to authenticate requests sent to your LangGraph
                server.
              </p>
              <PasswordInput
                id="apiKey"
                name="apiKey"
                defaultValue={apiKey ?? ""}
                className="bg-background"
                placeholder="lsv2_pt_..."
              />
            </div>

            <div className="mt-2 flex justify-end">
              <Button
                type="submit"
                size="lg"
              >
                Continue
                <ArrowRight className="size-5" />
              </Button>
            </div>
          </form>
        </div>
      </div>
    );
  }

  return <StreamSession apiKey={apiKey}>{children}</StreamSession>;
};

// Create a custom hook to use the context
export const useStreamContext = (): StreamContextType => {
  const context = useContext(StreamContext);
  if (context === undefined) {
    throw new Error("useStreamContext must be used within a StreamProvider");
  }
  return context;
};

export const useDirectSSEMessages = () => {
  const context = useContext(DirectSSEContext);
  if (context === undefined) {
    throw new Error("useDirectSSEMessages must be used within a StreamProvider");
  }
  return context;
};

export default StreamContext;
