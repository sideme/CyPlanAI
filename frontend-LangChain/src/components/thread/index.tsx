import { v4 as uuidv4 } from "uuid";
import { useEffect, useRef, useMemo, useCallback } from "react";
import { cn } from "@/lib/utils";
import { useStreamContext, useDirectSSEMessages } from "@/providers/Stream";
import { useState, FormEvent } from "react";
import type { StreamCheckpoint, StreamMessage } from "@/types/langgraph";
import { AssistantMessage, AssistantMessageLoading } from "./messages/ai";
import { HumanMessage } from "./messages/human";
import {
  DO_NOT_RENDER_ID_PREFIX,
  ensureToolCallsHaveResponses,
} from "@/lib/ensure-tool-responses";
import type { Message } from "@langchain/langgraph-sdk";
import { XIcon } from "lucide-react";
import { StickToBottom } from "use-stick-to-bottom";
import { toast } from "sonner";
import { useThreads } from "@/providers/Thread";
import { useAuth } from "@/providers/Auth";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { getContentString } from "./utils";
import { useFileUpload } from "@/hooks/use-file-upload";
import {
  useArtifactOpen,
  ArtifactContent,
  ArtifactTitle,
  useArtifactContext,
} from "./artifact";
import {
  getDefaultApiUrl,
  getDefaultAssistantId,
  useAppState,
} from "@/providers/AppState";
import { StickyToBottomContent, ScrollToBottom } from "./components/StickyScroll";
import { Sidebar } from "./components/Sidebar";
import { Header } from "./components/Header";
import { WelcomeScreen } from "./components/WelcomeScreen";
import { MessageInput } from "./components/MessageInput";
import { SettingsPanel } from "./components/SettingsPanel";
import { UserMenu } from "./components/UserMenu";
import { getApiKey } from "@/lib/api-key";

export function Thread() {
  const [artifactContext, setArtifactContext] = useArtifactContext();
  const [artifactOpen, closeArtifact] = useArtifactOpen();

  const { user, logout, token } = useAuth();
  const {
    threadId,
    setThreadId: setThreadIdContext,
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
  } = useAppState();
  const [input, setInput] = useState("");
  const {
    contentBlocks,
    setContentBlocks,
    handleFileUpload,
    dropRef,
    removeBlock,
    resetBlocks: _resetBlocks,
    dragOver,
    handlePaste,
  } = useFileUpload();
  const [firstTokenReceived, setFirstTokenReceived] = useState(false);
  const isLargeScreen = useMediaQuery("(min-width: 1024px)");
  const inputTextareaRef = useRef<HTMLTextAreaElement | null>(null);
  const [apiInput, setApiInput] = useState(apiUrl);
  const [assistantInput, setAssistantInput] = useState(assistantId);
  const [themeSelection, setThemeSelection] = useState(theme);
  const [footerMenuOpen, setFooterMenuOpen] = useState(false);
  const footerMenuRef = useRef<HTMLDivElement | null>(null);

  const stream = useStreamContext();
  const directSSE = useDirectSSEMessages();
  const hydratedThreadRef = useRef<string | null>(null);
  const previousThreadIdRef = useRef<string | null>(null);
  const { getThreads, setThreads, threads, renameThread } = useThreads();
  const currentThreadTitle = useMemo(() => {
    if (!threadId) return "";
    const thread = threads.find((t) => t.thread_id === threadId);
    if (!thread) return "";
    const metadata = (thread.metadata ?? {}) as Record<string, unknown>;
    const title =
      (metadata?.["title"] as string | undefined) ??
      (metadata?.["auto_title"] as string | undefined);
    if (title) return title;

    if (
      typeof thread.values === "object" &&
      thread.values &&
      "messages" in thread.values &&
      Array.isArray(thread.values.messages) &&
      thread.values.messages.length > 0
    ) {
      return (
        getContentString(thread.values.messages[0].content) ?? "New conversation"
      );
    }

    return "New conversation";
  }, [threadId, threads]);

  const handleRenameThread = useCallback(() => {
    if (!threadId) return;
    const defaultValue =
      currentThreadTitle && currentThreadTitle !== "New conversation"
        ? currentThreadTitle
        : "";
    const result = window.prompt("Enter a new conversation title", defaultValue);
    if (result === null) return;
    const trimmed = result.trim();
    renameThread(threadId, trimmed.length > 0 ? trimmed : null)
      .then(() => {
        toast.success("Conversation title updated");
        return getThreads().then(setThreads).catch(() => undefined);
      })
      .catch((error) => {
        toast.error("Unable to update conversation title", {
          description: error instanceof Error ? error.message : String(error),
        });
      });
  }, [threadId, currentThreadTitle, renameThread, getThreads, setThreads]);

  useEffect(() => {
    if (threadId !== previousThreadIdRef.current) {
      hydratedThreadRef.current = null;
      previousThreadIdRef.current = threadId;
    }
  }, [threadId]);

  useEffect(() => {
    if (!threadId) return;
    if (!apiUrl) return;
    if (hydratedThreadRef.current === threadId) return;
    const authToken = token ?? getApiKey();
    if (!authToken) return;

    const normalizedApiUrl = apiUrl.endsWith("/")
      ? apiUrl.slice(0, -1)
      : apiUrl;

    const controller = new AbortController();
    let cancelled = false;

    const hydrateThreadHistory = async () => {
      try {
        const response = await fetch(`${normalizedApiUrl}/threads/${threadId}/state`, {
          headers: {
            Authorization: `Bearer ${authToken}`,
          },
          signal: controller.signal,
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          const message =
            payload?.detail ??
            payload?.message ??
            `Failed to load conversation history (status ${response.status})`;
          throw new Error(message);
        }

        if (cancelled) return;

        const historyMessages = Array.isArray(payload?.values?.messages)
          ? (payload.values.messages as StreamMessage[])
          : [];

        directSSE.setMessages((previous) => {
          if (previous.length > 0) {
            return previous;
          }
          return historyMessages;
        });
        hydratedThreadRef.current = threadId;
      } catch (error) {
        if (controller.signal.aborted) return;
        console.error("Failed to hydrate conversation history", error);
        hydratedThreadRef.current = null;
      }
    };

    hydrateThreadHistory();

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [threadId, apiUrl, token, directSSE.setMessages]);
  
  // Get messages from all sources
  // 1. directSSE.messages - manually intercepted from SSE (most reliable)
  // 2. stream.values.messages - SDK's raw SSE data (may not update)
  // 3. stream.messages - SDK's processed messages (may have issues)
  const messagesFromDirectSSE = directSSE.messages as StreamMessage[];
  const messagesFromValues = Array.isArray(stream.values?.messages) 
    ? (stream.values.messages as StreamMessage[])
    : [];
  const messagesFromStream = Array.isArray(stream.messages) 
    ? (stream.messages as StreamMessage[])
    : [];
  
  // CRITICAL: Deduplicate messages - wrapped in useMemo to avoid repeated execution
  const finalMessages: StreamMessage[] = useMemo(() => {
    // Prioritize directSSE.messages (manually intercepted from SSE)
    const sourceMessages = messagesFromDirectSSE.length > 0 
      ? messagesFromDirectSSE 
      : messagesFromValues;

    const resolveId = (message: StreamMessage): string | undefined => {
      if (!message) return undefined;
      return (
        message.id ||
        (message as any).client_message_id ||
        (message.additional_kwargs as any)?.client_message_id ||
        (message.additional_kwargs as any)?.id
      );
    };

    // Get message signature for content-based deduplication
    const getMessageSignature = (message: StreamMessage): string => {
      if (!message) return "";
      const type = message.type ?? "";
      const content = Array.isArray(message.content)
        ? JSON.stringify(message.content)
        : typeof message.content === "string"
          ? message.content
          : JSON.stringify(message.content ?? "");
      return `${type}:${content}`;
    };

    // Deduplicate by both ID and content signature
    // For human messages, be more strict about content-based deduplication
    const seenIds = new Set<string>();
    const seenSignatures = new Set<string>();
    const result: StreamMessage[] = [];

    sourceMessages.forEach((message) => {
      if (!message) return;
      
      const msgId = resolveId(message);
      const signature = getMessageSignature(message);
      
      // For AI messages, allow updates even if ID is the same (for streaming updates)
      if (message.type === "ai" && msgId && seenIds.has(msgId)) {
        // If same ID, check if this is an update (different signature) or exact duplicate
        const existingIndex = result.findIndex(m => resolveId(m) === msgId);
        if (existingIndex >= 0) {
          const existingMsg = result[existingIndex];
          const existingSignature = getMessageSignature(existingMsg);
          if (existingSignature === signature) {
            // Exact duplicate, skip
            return;
          }
          // Different signature with same ID means update, replace the existing one
          result[existingIndex] = message;
          return;
        }
      }
      
      // Skip if we've seen this ID before (for non-AI messages)
      if (msgId && seenIds.has(msgId)) {
        return;
      }
      
      // For human messages, be more strict: skip if we've seen this exact content before
      // This prevents duplicate human messages from backend
      if (message.type === "human" && signature && seenSignatures.has(signature)) {
        return;
      }
      
      // For other message types (tool, etc.), also check signature but allow updates
      if (signature && seenSignatures.has(signature) && message.type !== "ai") {
        return;
      }
      
      if (msgId) {
        seenIds.add(msgId);
      }
      if (signature) {
        seenSignatures.add(signature);
      }
      
      result.push(message);
    });

    // Only use stream.messages if both directSSE and values.messages are empty
    if (result.length === 0 && messagesFromStream.length > 0) {
      return messagesFromStream as StreamMessage[];
    }
    
    return result;
  }, [messagesFromDirectSSE, messagesFromValues, messagesFromStream]);
  
  // Debug: Log which source we're using
  // Log both sources for debugging (only when messages change)
  const valuesHasAI = messagesFromValues.some(m => m?.type === "ai");
  const streamHasAI = messagesFromStream.some(m => m?.type === "ai");
  
  // Prefer values.messages when it contains additional assistant content.
  if (valuesHasAI && !streamHasAI && messagesFromValues.length > messagesFromStream.length) {
    // No action needed; we already prioritize values.messages above.
  }
  
  // Debug: Log the actual data we're using for rendering
  useEffect(() => {
    if (finalMessages.length > 0) {
      // Monitor messages used for rendering.
    }
  }, [finalMessages.length, finalMessages.map(m => m?.id).join(",")]);
  
  const hasAIMessage = finalMessages.some(m => m.type === "ai");
  const hasHumanMessage = finalMessages.some(m => m.type === "human");

  const isLoading = stream.isLoading;

  // Track previous message count to only log when messages actually change
  const prevMessageCountRef = useRef(0);
  const prevMessageIdsRef = useRef<string[]>([]);
  
  // Only log when messages actually change (count or content)
  useEffect(() => {
    const currentMessageIds = finalMessages.map(m => m.id || '').filter(Boolean);
    const messageCount = finalMessages.length;
    const prevCount = prevMessageCountRef.current;
    const prevIds = prevMessageIdsRef.current;
    
    // Only log if:
    // 1. Message count changed, OR
    // 2. Message IDs changed (new messages added), OR
    // 3. We have messages and isLoading just changed to false (stream completed)
    const messagesChanged = 
      messageCount !== prevCount ||
      JSON.stringify(currentMessageIds) !== JSON.stringify(prevIds) ||
      (messageCount > 0 && !isLoading && prevCount === 0);
    
    if (messagesChanged && messageCount > 0) {
      prevMessageCountRef.current = messageCount;
      prevMessageIdsRef.current = currentMessageIds;
    } else if (messagesChanged && messageCount === 0 && prevCount > 0) {
      // Messages were cleared
      prevMessageCountRef.current = 0;
      prevMessageIdsRef.current = [];
    }
  }, [finalMessages.length, hasAIMessage, isLoading, finalMessages, messagesFromValues]);

  const lastError = useRef<string | undefined>(undefined);

  const setThreadId = (id: string | null) => {
    // If creating a new thread, first refresh threads list to save current thread to history
    if (id === null && threadId) {
      // Refresh threads list to ensure current thread is saved to history
      getThreads()
        .then(setThreads)
        .catch(() => undefined);
    }
    
    // Clear messages when switching threads (including switching to a different thread)
    // This prevents messages from accumulating when clicking on different history chats.
    // EXCEPTION: If transitioning from null (creating new) to a valid ID, DO NOT clear,
    // because we likely have an optimistic message that triggered this creation.
    if (id !== threadId && !(threadId === null && id !== null)) {
      directSSE.setMessages([]);
    }
    
    setThreadIdContext(id);

    // close artifact and reset artifact context
    closeArtifact();
    setArtifactContext({});
  };

  const handleComingSoon = useCallback(() => {
    toast("Coming soon!");
  }, []);

  const handleSaveSettings = useCallback(async () => {
    const normalizedApi = apiInput.trim() || getDefaultApiUrl();
    const normalizedAssistant = assistantInput.trim() || getDefaultAssistantId();
    setApiUrl(normalizedApi);
    setAssistantId(normalizedAssistant);
    setTheme(themeSelection);
    
    // Sync to backend after a short delay to ensure state is updated
    setTimeout(() => {
      syncPreferences().catch((err) => {
        console.error("Failed to sync preferences to server:", err);
      });
    }, 100);
    
    toast.success("Settings saved");
    setSettingsOpen(false);
  }, [
    apiInput,
    assistantInput,
    setApiUrl,
    setAssistantId,
    themeSelection,
    setTheme,
    setSettingsOpen,
    syncPreferences,
  ]);
  const handleQuickPrompt = useCallback(
    (value: string) => {
      if (isLoading) return;
      setFirstTokenReceived(false);

      const newHumanMessage: StreamMessage = {
        id: uuidv4(),
        type: "human",
        content: [
          { type: "text", text: value },
        ] as StreamMessage["content"],
      };

      const toolMessages = ensureToolCallsHaveResponses(
        finalMessages as unknown as Message[],
      ) as unknown as StreamMessage[];

      const context =
        Object.keys(artifactContext).length > 0 ? artifactContext : undefined;

      directSSE.addOptimisticMessage({ ...newHumanMessage, clientOptimistic: true });

      // Note: LangGraph SDK should automatically create a thread when threadId is null
      // via the onThreadId callback. The stream.submit will trigger thread creation.
      stream.submit(
        {
          messages: [...toolMessages, newHumanMessage] as unknown as Message[],
          context,
        },
        {
          streamMode: ["values", "updates"],
          streamSubgraphs: true,
          streamResumable: true,
          optimisticValues: (prev: Record<string, any>) => ({
            ...prev,
            context,
            messages: [
              ...(prev.messages ?? []),
              ...toolMessages,
              newHumanMessage,
            ],
          }),
        },
      );

      setInput("");
      setContentBlocks([]);
    },
    [isLoading, finalMessages, artifactContext, directSSE, stream, setFirstTokenReceived, setInput, setContentBlocks],
  );

  const quickPrompts = useMemo(
    () => [
      {
        title: "Start a readiness checklist",
        description: "Draft an ISO 27001 readiness checklist for our next audit.",
        value:
          "Generate an ISO 27001 readiness checklist for our organization, highlighting the top gaps to close before the next audit.",
      },
      {
        title: "Summarize compliance plan",
        description: "Turn my compliance plan notes into a concise brief.",
        value:
          "Summarize my latest cybersecurity compliance plan into key actions, stakeholders, and milestones.",
      },
      {
        title: "Explain control requirements",
        description: "Break down NIST CSF PR.AC controls in simple terms.",
        value:
          "Explain the NIST CSF PR.AC (Access Control) category in simple language for business stakeholders.",
      },
      {
        title: "Awareness training ideas",
        description: "Outline topics for next month's awareness session.",
        value:
          "Create a cybersecurity awareness session outline for next month focused on phishing and credential safety.",
      },
    ],
    [],
  );

  useEffect(() => {
    if (!stream.error) {
      lastError.current = undefined;
      return;
    }
    try {
      const message = (stream.error as any).message;
      if (!message || lastError.current === message) {
        // Message has already been logged. do not modify ref, return early.
        return;
      }

      // Message is defined, and it has not been logged yet. Save it, and send the error
      lastError.current = message;
      toast.error("An error occurred. Please try again.", {
        description: (
          <p>
            <strong>Error:</strong> <code>{message}</code>
          </p>
        ),
        richColors: true,
        closeButton: true,
      });
    } catch {
      // no-op
    }
  }, [stream.error]);

  useEffect(() => {
    setApiInput(apiUrl);
  }, [apiUrl]);

  useEffect(() => {
    setAssistantInput(assistantId);
  }, [assistantId]);

  useEffect(() => {
    setThemeSelection(theme);
  }, [theme]);

  useEffect(() => {
    const handleOutside = (event: MouseEvent) => {
      if (
        footerMenuRef.current &&
        !footerMenuRef.current.contains(event.target as Node)
      ) {
        setFooterMenuOpen(false);
      }
    };

    document.addEventListener("mousedown", handleOutside);
    return () => {
      document.removeEventListener("mousedown", handleOutside);
    };
  }, []);

  // TODO: this should be part of the useStream hook
  const prevMessageLength = useRef(0);
  useEffect(() => {
    if (
      finalMessages.length !== prevMessageLength.current &&
      finalMessages?.length &&
      finalMessages[finalMessages.length - 1].type === "ai"
    ) {
      setFirstTokenReceived(true);
    }

    prevMessageLength.current = finalMessages.length;
  }, [finalMessages]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if ((input.trim().length === 0 && contentBlocks.length === 0) || isLoading)
      return;
    setFirstTokenReceived(false);

    const newHumanMessage: StreamMessage = {
      id: uuidv4(),
      type: "human",
      content: [
        ...(input.trim().length > 0 ? [{ type: "text", text: input }] : []),
        ...contentBlocks,
      ] as StreamMessage["content"],
    };

    const toolMessages = ensureToolCallsHaveResponses(
      finalMessages as unknown as Message[],
    ) as unknown as StreamMessage[];

    const context =
      Object.keys(artifactContext).length > 0 ? artifactContext : undefined;

    directSSE.addOptimisticMessage({ ...newHumanMessage, clientOptimistic: true });

    // Note: LangGraph SDK should automatically create a thread when threadId is null
    // via the onThreadId callback. The stream.submit will trigger thread creation.
    stream.submit(
      {
        messages: [...toolMessages, newHumanMessage] as unknown as Message[],
        context,
      },
      {
        streamMode: ["values", "updates"],
        streamSubgraphs: true,
        streamResumable: true,
        optimisticValues: (prev: Record<string, any>) => ({
          ...prev,
          context,
          messages: [
            ...(prev.messages ?? []),
            ...toolMessages,
            newHumanMessage,
          ],
        }),
      },
    );

    setInput("");
    setContentBlocks([]);
  };

  const handleRegenerate = (
    parentCheckpoint: StreamCheckpoint | null | undefined,
  ) => {
    // Do this so the loading state is correct
    prevMessageLength.current = prevMessageLength.current - 1;
    setFirstTokenReceived(false);
    stream.submit(undefined, {
      checkpoint: parentCheckpoint as any,
      streamMode: ["values"],
      streamSubgraphs: true,
      streamResumable: true,
    });
  };

  const chatStarted = !!threadId || !!finalMessages.length;
  const hasNoAIOrToolMessages = !finalMessages.find(
    (m) => m.type === "ai" || m.type === "tool",
  );

  return (
    <div
      className={cn(
        "flex h-screen w-full overflow-hidden bg-background text-foreground",
        !chatStarted && "dark:bg-[#050B15] dark:text-slate-100",
      )}
    >
      {/* Large screen: sidebar section - always rendered to prevent layout jumps */}
      {isLargeScreen && (
        <Sidebar
          chatHistoryOpen={chatHistoryOpen}
          setChatHistoryOpen={setChatHistoryOpen}
          onNewChat={() => setThreadId(null)}
          onSearch={() => setSearchOpen(true)}
          onComingSoon={handleComingSoon}
          userInitials={user?.name?.slice(0, 2).toUpperCase() ?? "U"}
          onProfileClick={() => setFooterMenuOpen((prev) => !prev)}
        />
      )}

      <div
        className={cn(
          "grid min-w-0 flex-1 grid-cols-[1fr_0fr] transition-all duration-500",
          artifactOpen && "grid-cols-[3fr_2fr]",
        )}
      >
        <div
          className={cn(
            "relative flex min-w-0 flex-1 flex-col overflow-hidden",
            !chatStarted && "grid-rows-[1fr]",
          )}
        >
          <Header
            chatStarted={chatStarted}
            isLargeScreen={isLargeScreen}
            chatHistoryOpen={chatHistoryOpen}
            setChatHistoryOpen={setChatHistoryOpen}
            onNewChat={() => setThreadId(null)}
            threadId={threadId}
            onRenameThread={handleRenameThread}
            user={user}
            onLogout={logout}
          />

          <StickToBottom className="relative flex-1 overflow-hidden">
            <StickyToBottomContent
              className={cn(
                "absolute inset-0 px-4 [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-track]:bg-transparent",
                chatStarted
                  ? "overflow-y-scroll [&::-webkit-scrollbar-thumb]:bg-gray-300 grid grid-rows-[1fr_auto]"
                  : "overflow-hidden flex flex-col",
              )}
              contentClassName={cn(
                "mx-auto flex w-full max-w-3xl flex-col gap-4",
                chatStarted ? "pb-16 pt-8" : "h-full max-w-4xl items-center justify-center gap-6 text-center overflow-hidden py-4",
              )}
              content={
                <>
                  {finalMessages.length === 0 && !threadId ? (
                    <WelcomeScreen
                      user={user}
                      input={input}
                      setInput={setInput}
                      contentBlocks={contentBlocks}
                      handleFileUpload={handleFileUpload}
                      removeBlock={removeBlock}
                      handleSubmit={handleSubmit}
                      isLoading={isLoading}
                      quickPrompts={quickPrompts}
                      onQuickPrompt={handleQuickPrompt}
                    />
                  ) : (
                    <>
                      {(() => {
                        const filteredMessages = finalMessages.filter((m) => {
                          return !m.id?.startsWith(DO_NOT_RENDER_ID_PREFIX);
                        });
                        const typedMessages = filteredMessages as unknown as Message[];

                        return typedMessages.map((message, index) =>
                          message.type === "human" ? (
                            <HumanMessage
                              key={message.id || `human-${index}`}
                              message={message}
                              isLoading={isLoading}
                            />
                          ) : message.type === "ai" ? (
                            <AssistantMessage
                              key={message.id || `ai-${index}`}
                              message={message}
                              isLoading={isLoading}
                              handleRegenerate={handleRegenerate}
                            />
                          ) : (
                            <div key={message.id || `unknown-${index}`} className="text-red-500">
                              Unknown message type: {message.type}
                            </div>
                          )
                        );
                      })()}
                      {/* Special rendering case where there are no AI/tool messages, but there is an interrupt.
                        We need to render it outside of the messages list, since there are no messages to render */}
                      {hasNoAIOrToolMessages && !!stream.interrupt && (
                        <AssistantMessage
                          key="interrupt-msg"
                          message={undefined}
                          isLoading={isLoading}
                          handleRegenerate={handleRegenerate}
                        />
                      )}
                      {isLoading && !firstTokenReceived && (
                        <AssistantMessageLoading />
                      )}
                    </>
                  )}
                </>
              }
              footer={
                <div
                  className={cn(
                    "sticky bottom-0 flex flex-col items-center gap-8 bg-background",
                    !chatStarted &&
                      "border-t border-border bg-background/90 text-foreground backdrop-blur-lg",
                  )}
                >
                  <ScrollToBottom className="animate-in fade-in-0 zoom-in-95 absolute bottom-full left-1/2 mb-4 -translate-x-1/2" />

                  {chatStarted && (
                    <MessageInput
                      input={input}
                      setInput={setInput}
                      contentBlocks={contentBlocks}
                      handleFileUpload={handleFileUpload}
                      removeBlock={removeBlock}
                      handlePaste={handlePaste}
                      handleSubmit={handleSubmit}
                      isLoading={isLoading}
                      dragOver={dragOver}
                      dropRef={dropRef}
                      onStop={() => stream.stop()}
                    />
                  )}
                </div>
              }
            />
          </StickToBottom>
        </div>
        <div className="relative flex flex-col border-l">
          <div className="absolute inset-0 flex min-w-[30vw] flex-col">
            <div className="grid grid-cols-[1fr_auto] border-b p-4">
              <ArtifactTitle className="truncate overflow-hidden" />
              <button
                onClick={closeArtifact}
                className="cursor-pointer"
              >
                <XIcon className="size-5" />
              </button>
            </div>
            <ArtifactContent className="relative flex-grow" />
          </div>
        </div>
      </div>

      <SettingsPanel
        open={settingsOpen}
        onOpenChange={setSettingsOpen}
        theme={theme}
        themeSelection={themeSelection}
        setThemeSelection={setThemeSelection}
        setTheme={setTheme}
        hideToolCalls={hideToolCalls}
        setHideToolCalls={setHideToolCalls}
        apiInput={apiInput}
        setApiInput={setApiInput}
        assistantInput={assistantInput}
        setAssistantInput={setAssistantInput}
        onSave={handleSaveSettings}
      />

      <UserMenu
        open={footerMenuOpen && !chatHistoryOpen}
        menuRef={footerMenuRef}
        user={user}
        onSettings={() => {
          setSettingsOpen(true);
          setFooterMenuOpen(false);
        }}
        onLogout={() => {
          logout();
          setFooterMenuOpen(false);
        }}
      />
    </div>
  );
}
