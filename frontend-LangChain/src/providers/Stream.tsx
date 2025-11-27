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
import { CyPlanAILogoSVG } from "@/components/icons/cyplanai";
import { Label } from "@/components/ui/label";
import { ArrowRight } from "lucide-react";
import { PasswordInput } from "@/components/ui/password-input";
import { getApiKey } from "@/lib/api-key";
import { useThreads } from "./Thread";
import { toast } from "sonner";
import { useAppState } from "./AppState";
import { useAuth } from "./Auth";

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

// Extract just the text content for fuzzy matching (ignoring attachments/files differences)
const getTextContent = (message: StreamMessage): string => {
  if (!message?.content) return "";
  if (typeof message.content === "string") return message.content;
  if (Array.isArray(message.content)) {
    return message.content
      .filter((c: any) => c.type === "text")
      .map((c: any) => c.text)
      .join("");
  }
  return "";
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
  const prevThreadIdRef = useRef<string | null>(threadId);
  
  useEffect(() => {
    directSSEMessagesRef.current = directSSEMessages;
  }, [directSSEMessages]);
  
  // Clear messages when threadId changes to prevent message accumulation
  // BUT: Don't clear if we're creating a new thread (null -> new_id)
  // This prevents the flash of empty screen when sending first message
  useEffect(() => {
    if (prevThreadIdRef.current !== threadId) {
      const isCreatingNewThread = prevThreadIdRef.current === null && threadId !== null;
      
      // Only clear if we're switching to a different existing thread, not creating a new one
      // When creating a new thread, we want to keep the optimistic message
      if (!isCreatingNewThread) {
        setDirectSSEMessages([]);
        directSSEMessagesRef.current = [];
      }
      prevThreadIdRef.current = threadId;
    }
  }, [threadId]);
  
  const streamValue = useTypedStream({
    apiUrl,
    apiKey: apiKey ?? undefined,
    assistantId,
    threadId: threadId ?? null,
    fetchStateHistory: true,
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
            const canonicalId =
              getCanonicalId(msg) ?? msg.id ?? crypto.randomUUID();

            // First, try to match by optimistic message signature OR text content (ignoring attachments)
            const optimisticIndex = nextMessages.findIndex((m) => {
              if (!Boolean(m?.clientOptimistic)) return false;
              // Exact match
              if (getMessageSignature(m) === signature) return true;
              // Fuzzy text match for human messages (optimistic has file, backend response might not)
              if (m.type === "human" && msg.type === "human") {
                const textA = getTextContent(m).trim();
                const textB = getTextContent(msg).trim();
                return textA.length > 0 && textA === textB;
              }
              return false;
            });

            if (optimisticIndex !== -1) {
              const existingMessage = nextMessages[optimisticIndex];
              const resolvedId = (msg.id ?? existingMessage.id ?? crypto.randomUUID()) as string;
              nextMessages[optimisticIndex] = {
                ...existingMessage,
                ...msg,
                // If merging backend message into optimistic, we might lose attachments if we are not careful
                // But mergeOptimisticContent handles this
                content: mergeOptimisticContent(existingMessage, msg),
                // Preserve tool_calls from incoming message
                tool_calls: (msg as any)?.tool_calls ?? (existingMessage as any)?.tool_calls,
                id: resolvedId,
                clientOptimistic: false,
              };
              return;
            }

            // Then, try to match by canonical ID
            const existingIndexById = nextMessages.findIndex(
              (m) =>
                getCanonicalId(m) === canonicalId ||
                (m.id ?? "") === (msg.id ?? ""),
            );
            if (existingIndexById >= 0) {
              nextMessages[existingIndexById] = {
                ...nextMessages[existingIndexById],
                ...msg,
                content: mergeOptimisticContent(nextMessages[existingIndexById], msg),
                // Preserve tool_calls from incoming message
                tool_calls: (msg as any)?.tool_calls ?? (nextMessages[existingIndexById] as any)?.tool_calls,
                id: msg.id ?? nextMessages[existingIndexById].id ?? canonicalId,
                clientOptimistic: false,
              };
              return;
            }

            // Finally, check for duplicate by content signature OR text content (for messages without ID or with different IDs)
            const existingIndexBySignature = nextMessages.findIndex((m) => {
              if (Boolean(m?.clientOptimistic)) return false; // Already checked optimistic above
              
              // Exact signature match
              if (getMessageSignature(m) === signature) return true;
              
              // Fuzzy text match for human messages
              if (m.type === "human" && msg.type === "human") {
                const textA = getTextContent(m).trim();
                const textB = getTextContent(msg).trim();
                // Only match if text is substantial to avoid false positives on empty/short messages
                return textA.length > 5 && textA === textB;
              }
              return false;
            });
            
            if (existingIndexBySignature >= 0) {
              // Update existing message with same content but keep the original ID
              nextMessages[existingIndexBySignature] = {
                ...nextMessages[existingIndexBySignature],
                ...msg,
                content: mergeOptimisticContent(nextMessages[existingIndexBySignature], msg),
                // Preserve tool_calls from incoming message
                tool_calls: (msg as any)?.tool_calls ?? (nextMessages[existingIndexBySignature] as any)?.tool_calls,
                id: nextMessages[existingIndexBySignature].id ?? msg.id ?? canonicalId,
                clientOptimistic: false,
              };
              return;
            }

            // New message, add it
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

      // Process incoming messages: replace optimistic, dedupe by ID and signature
      // IMPORTANT: Maintain the order of incoming messages
      const processedMessages: StreamMessage[] = [];
      const matchedOptimisticIndexes = new Set<number>();
      const seenCanonicalIds = new Set<string>();
      const seenSignatures = new Set<string>();
      
      incomingMessages.forEach((msg: StreamMessage) => {
        const canonicalId = getCanonicalId(msg);
        const effectiveId = canonicalId ?? msg?.id ?? crypto.randomUUID();
        const signature = getMessageSignature(msg);
        
        // Skip if we've already processed this ID in this batch
        if (seenCanonicalIds.has(effectiveId)) {
          return;
        }
        
        // Skip if we've already processed this exact content in this batch
        if (signature && seenSignatures.has(signature)) {
          return;
        }
        
        seenCanonicalIds.add(effectiveId);
        if (signature) {
          seenSignatures.add(signature);
        }
        
        // Check if this matches an optimistic message
        const optimisticIndex = existingOptimistic.findIndex((existing, idx) => {
          if (matchedOptimisticIndexes.has(idx)) return false;
          // Exact signature match
          if (getMessageSignature(existing) === signature) return true;
          
          // Fuzzy text match for human messages (optimistic has file, backend response might not)
          if (existing.type === "human" && msg.type === "human") {
            const textA = getTextContent(existing).trim();
            const textB = getTextContent(msg).trim();
            return textA.length > 0 && textA === textB;
          }
          return false;
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
            // Preserve tool_calls from incoming message (backend has the correct tool_calls)
            tool_calls: (msg as any)?.tool_calls ?? (optimisticMessage as any)?.tool_calls,
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
            // Preserve tool_calls from incoming message (backend has the correct tool_calls)
            tool_calls: (msg as any)?.tool_calls ?? (existing as any)?.tool_calls,
            id: msg.id ?? existing.id ?? canonicalId,
            clientOptimistic: false,
          });
          existingByCanonical.delete(canonicalId);
        } else {
          // Check if we already have a message with the same content signature OR text content
          const existingBySignature = existingMessages.find((m) => {
            if (Boolean(m?.clientOptimistic)) return false; // Already processed optimistic
            // Exact signature match
            if (getMessageSignature(m) === signature) return true;
            
            // Fuzzy text match for human messages
            if (m.type === "human" && msg.type === "human") {
              const textA = getTextContent(m).trim();
              const textB = getTextContent(msg).trim();
              return textA.length > 5 && textA === textB;
            }
            return false;
          });
          
          if (existingBySignature) {
            // Update existing message with same content
            processedMessages.push({
              ...existingBySignature,
              ...msg,
              content: mergeOptimisticContent(existingBySignature, msg),
              // Preserve tool_calls from incoming message
              tool_calls: (msg as any)?.tool_calls ?? (existingBySignature as any)?.tool_calls,
              id: existingBySignature.id ?? msg.id ?? effectiveId,
              clientOptimistic: false,
            });
          } else {
            // New message
            const fallbackCanonical = canonicalId ?? effectiveId;
            processedMessages.push({
              ...msg,
              id: msg.id ?? fallbackCanonical,
              clientOptimistic: false,
            });
          }
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

      // CRITICAL: Maintain chronological order
      // Backend may only send current round's messages, not full history
      // So we need to merge: [historical messages] + [new messages from backend] + [optimistic]
      const combined = dedupeByCanonicalId([
        ...preservedHistorical,
        ...processedMessages,
        ...preservedOptimistic,
      ]);
      
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
  const { token } = useAuth();

  // For API key, use localStorage with env var fallback
  const [apiKey, _setApiKey] = useState(() => {
    const storedKey = getApiKey();
    return storedKey || "";
  });

  const setApiKey = (key: string) => {
    window.localStorage.setItem("lg:chat:apiKey", key);
    _setApiKey(key);
  };

  useEffect(() => {
    if (token) {
      _setApiKey(token);
    } else {
      _setApiKey("");
    }
  }, [token]);

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
              <CyPlanAILogoSVG className="h-7" />
              <h1 className="text-xl font-semibold tracking-tight">
                CyPlanAI
              </h1>
            </div>
            <p className="text-muted-foreground">
              Welcome to CyPlanAI! Before you get started, you need to enter
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
