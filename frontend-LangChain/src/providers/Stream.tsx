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

const getCanonicalId = (message?: StreamMessage): string | undefined => {
  if (!message) return undefined;
  const additional =
    ((message as Record<string, unknown>)?.additional_kwargs ??
      {}) as Record<string, unknown>;
  const directClientId = (message as Record<string, unknown>)?.[
    "client_message_id"
  ];
  return (
    (additional?.["client_message_id"] as string | undefined) ??
    (directClientId as string | undefined) ??
    (message.id as string | undefined) ??
    (additional?.["id"] as string | undefined)
  );
};

const dedupeByCanonicalId = (messages: StreamMessage[]): StreamMessage[] => {
  const order: string[] = [];
  const map = new Map<string, StreamMessage>();
  const withoutId: StreamMessage[] = [];

  messages.forEach((msg) => {
    const canonicalId = getCanonicalId(msg);
    if (!canonicalId) {
      withoutId.push({ ...msg });
      return;
    }

    if (!map.has(canonicalId)) {
      order.push(canonicalId);
    }

    map.set(canonicalId, {
      ...msg,
      clientOptimistic: Boolean(msg?.clientOptimistic),
    });
  });

  return [...order.map((key) => map.get(key)!), ...withoutId];
};

const toTextBlock = (value: unknown) => {
  if (value == null) return undefined;
  if (typeof value === "object" && value && "type" in (value as any)) {
    return value;
  }
  return { type: "text", text: String(value) };
};

const mergeOptimisticContent = (
  optimistic?: StreamMessage,
  incoming?: StreamMessage,
): StreamMessage["content"] => {
  const optimisticContent = optimistic?.content;
  const incomingContent = incoming?.content;

  const attachments: any[] = [];
  if (Array.isArray(optimisticContent)) {
    optimisticContent.forEach((item) => {
      if (
        item &&
        typeof item === "object" &&
        "type" in item &&
        (item as any).type !== "text"
      ) {
        attachments.push(item);
      }
    });
  }

  const textBlocks: any[] = [];
  if (typeof incomingContent === "string") {
    textBlocks.push({ type: "text", text: incomingContent });
  } else if (Array.isArray(incomingContent)) {
    incomingContent.forEach((item) => {
      // Skip file/image blocks - they should come from optimistic message
      if (
        item &&
        typeof item === "object" &&
        "type" in item &&
        (item as any).type !== "text"
      ) {
        return; // Skip non-text blocks from incoming message
      }
      const block = toTextBlock(item);
      if (block) textBlocks.push(block);
    });
  } else if (incomingContent != null) {
    // Skip file/image blocks from incoming message
    if (
      typeof incomingContent === "object" &&
      "type" in (incomingContent as any) &&
      (incomingContent as any).type !== "text"
    ) {
      // Don't add non-text blocks from incoming message
    } else {
      const block = toTextBlock(incomingContent);
      if (block) textBlocks.push(block);
    }
  }

  if (textBlocks.length === 0 && Array.isArray(optimisticContent)) {
    optimisticContent.forEach((item) => {
      if (
        item &&
        typeof item === "object" &&
        (item as any).type === "text"
      ) {
        textBlocks.push(item);
      }
    });
  }

  if (attachments.length === 0) {
    if (textBlocks.length > 0) return textBlocks;
    return incomingContent ?? optimisticContent;
  }

  return [...attachments, ...textBlocks];
};

const messagesAreEqual = (
  a: StreamMessage[],
  b: StreamMessage[],
): boolean => {
  if (a.length !== b.length) {
    return false;
  }

  for (let i = 0; i < a.length; i += 1) {
    const aMsg = a[i];
    const bMsg = b[i];
    const aKey = getCanonicalId(aMsg) ?? aMsg.id ?? `idx-${i}`;
    const bKey = getCanonicalId(bMsg) ?? bMsg.id ?? `idx-${i}`;
    if (aKey !== bKey) {
      return false;
    }

    if (JSON.stringify(aMsg) !== JSON.stringify(bMsg)) {
      return false;
    }
  }
  return true;
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
                content: mergeOptimisticContent(existingMessage, msg),
                id: resolvedId,
                clientOptimistic: false,
              };
              return;
            }

            const canonicalId =
              getCanonicalId(msg) ?? msg.id ?? crypto.randomUUID();

            const existingIndex = nextMessages.findIndex(
              (m) =>
                getCanonicalId(m) === canonicalId ||
                (m.id ?? "") === (msg.id ?? ""),
            );
            if (existingIndex >= 0) {
              nextMessages[existingIndex] = {
                ...nextMessages[existingIndex],
                ...msg,
                content: mergeOptimisticContent(nextMessages[existingIndex], msg),
                id: msg.id ?? nextMessages[existingIndex].id ?? canonicalId,
                clientOptimistic: false,
              };
              return;
            }

            nextMessages.push({
              ...msg,
              id: msg.id ?? canonicalId,
              clientOptimistic: false,
            });
          });
        }
      });
      if (nextMessages.length > 0) {
        const deduped = dedupeByCanonicalId(nextMessages);
        if (messagesAreEqual(deduped, directSSEMessagesRef.current)) {
          return;
        }
        setDirectSSEMessages(deduped);
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
      
      // Build a map of existing messages by ID for efficient lookup
      const existingByCanonical = new Map<string, StreamMessage>();
      const existingOptimistic: StreamMessage[] = [];
      
      existingMessages.forEach((msg) => {
        if (msg?.clientOptimistic) {
          existingOptimistic.push(msg);
        } else if (msg?.id) {
          const canonicalId = getCanonicalId(msg) ?? msg.id;
          existingByCanonical.set(canonicalId, msg);
        }
      });

      // Process incoming messages: replace optimistic, dedupe by ID
      // IMPORTANT: Maintain the order of incoming messages
      const processedMessages: StreamMessage[] = [];
      const matchedOptimisticIndexes = new Set<number>();
      const seenCanonicalIds = new Set<string>();
      
      incomingMessages.forEach((msg: StreamMessage) => {
        const canonicalId = getCanonicalId(msg);
        const effectiveId = canonicalId ?? msg?.id ?? crypto.randomUUID();
        
        // Skip if we've already processed this ID in this batch
        if (seenCanonicalIds.has(effectiveId)) {
          console.log(
            `[SSE] Skipping duplicate message in incoming batch: ${effectiveId.substring(
              0,
              8,
            )}...`,
          );
          return;
        }
        
        seenCanonicalIds.add(effectiveId);
        
        // Check if this matches an optimistic message
        const signature = getMessageSignature(msg);
        const optimisticIndex = existingOptimistic.findIndex((existing, idx) => {
          if (matchedOptimisticIndexes.has(idx)) return false;
          return getMessageSignature(existing) === signature;
        });

        if (optimisticIndex !== -1) {
          // Replace optimistic message
          matchedOptimisticIndexes.add(optimisticIndex);
          const optimisticMessage = existingOptimistic[optimisticIndex];
          const finalCanonicalId =
            canonicalId ??
            getCanonicalId(optimisticMessage) ??
            crypto.randomUUID();
          processedMessages.push({
            ...optimisticMessage,
            ...msg,
            content: mergeOptimisticContent(optimisticMessage, msg),
            id: msg.id ?? optimisticMessage.id ?? finalCanonicalId,
            clientOptimistic: false,
          });
        } else if (canonicalId && existingByCanonical.has(canonicalId)) {
          // Message already exists (by ID), just use the incoming version (it may have updates)
          const existing = existingByCanonical.get(canonicalId)!;
          processedMessages.push({
            ...existing,
            ...msg,
            content: mergeOptimisticContent(existing, msg),
            id: msg.id ?? existing.id ?? canonicalId,
            clientOptimistic: false,
          });
          existingByCanonical.delete(canonicalId);
        } else {
          // New message
          const fallbackCanonical = canonicalId ?? effectiveId;
          processedMessages.push({
            ...msg,
            id: msg.id ?? fallbackCanonical,
            clientOptimistic: false,
          });
        }
      });

      // Preserve unmatched optimistic messages
      const preservedOptimistic = existingOptimistic.filter((_, idx) => !matchedOptimisticIndexes.has(idx));
      
      // Preserve existing messages that weren't in the incoming batch (historical messages)
      // Keep them in their original order from existingMessages
      // IMPORTANT: We need to maintain chronological order
      const processedIds = new Set(processedMessages.map(m => getCanonicalId(m) ?? m.id));
      const preservedHistorical: StreamMessage[] = [];
      existingMessages.forEach((msg) => {
        if (!msg?.clientOptimistic && msg?.id) {
          const canonicalId = getCanonicalId(msg) ?? msg.id;
          // Only include if it wasn't in the incoming batch
          if (!processedIds.has(canonicalId) && existingByCanonical.has(canonicalId)) {
            preservedHistorical.push(msg);
          }
        }
      });

      // Debug: Log message order
      console.log('[SSE-ORDER] === Message Order Debug ===');
      console.log('[SSE-ORDER] Incoming from backend:', incomingMessages.length, 'messages');
      incomingMessages.forEach((msg, idx) => {
        const msgId = getCanonicalId(msg) ?? msg?.id;
        const contentPreview = typeof msg.content === 'string' 
          ? msg.content.substring(0, 50) 
          : Array.isArray(msg.content) 
            ? JSON.stringify(msg.content).substring(0, 50)
            : '';
        console.log(`[SSE-ORDER]   [${idx}] ${msg.type} | ID: ${msgId?.substring(0, 8)}... | ${contentPreview}...`);
      });
      
      console.log('[SSE-ORDER] Processed messages:', processedMessages.length);
      processedMessages.forEach((msg, idx) => {
        const msgId = getCanonicalId(msg) ?? msg?.id;
        const contentPreview = typeof msg.content === 'string' 
          ? msg.content.substring(0, 50) 
          : Array.isArray(msg.content) 
            ? JSON.stringify(msg.content).substring(0, 50)
            : '';
        console.log(`[SSE-ORDER]   [${idx}] ${msg.type} | ID: ${msgId?.substring(0, 8)}... | ${contentPreview}...`);
      });
      
      console.log('[SSE-ORDER] Preserved historical:', preservedHistorical.length);
      preservedHistorical.forEach((msg, idx) => {
        const msgId = getCanonicalId(msg) ?? msg?.id;
        const contentPreview = typeof msg.content === 'string' 
          ? msg.content.substring(0, 50) 
          : Array.isArray(msg.content) 
            ? JSON.stringify(msg.content).substring(0, 50)
            : '';
        console.log(`[SSE-ORDER]   [${idx}] ${msg.type} | ID: ${msgId?.substring(0, 8)}... | ${contentPreview}...`);
      });

      // CRITICAL: Maintain chronological order
      // Backend may only send current round's messages, not full history
      // So we need to merge: [historical messages] + [new messages from backend] + [optimistic]
      const combined = dedupeByCanonicalId([
        ...preservedHistorical,
        ...processedMessages,
        ...preservedOptimistic,
      ]);
      
      console.log('[SSE-ORDER] Final combined:', combined.length);
      combined.forEach((msg, idx) => {
        const msgId = getCanonicalId(msg) ?? msg?.id;
        const contentPreview = typeof msg.content === 'string' 
          ? msg.content.substring(0, 50) 
          : Array.isArray(msg.content) 
            ? JSON.stringify(msg.content).substring(0, 50)
            : '';
        console.log(`[SSE-ORDER]   [${idx}] ${msg.type} | ID: ${msgId?.substring(0, 8)}... | ${contentPreview}...`);
      });
      
      if (messagesAreEqual(combined, directSSEMessagesRef.current)) {
        return;
      }
      setDirectSSEMessages(combined);
    } else if (currentMessages.length > 0 && directSSEMessagesRef.current.length === 0) {
      const normalized = dedupeByCanonicalId(
        currentMessages as StreamMessage[],
      );
      setDirectSSEMessages(normalized);
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
