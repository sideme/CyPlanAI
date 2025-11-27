import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useThreads } from "@/providers/Thread";
import { Thread } from "@langchain/langgraph-sdk";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { formatDistanceToNow } from "date-fns";

import { getContentString } from "../utils";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import {
  History,
  MessageSquare,
  MoreHorizontal,
  PanelRightClose,
  PanelRightOpen,
  Plus,
  Search,
  Settings,
  X,
} from "lucide-react";
import { CyPlanAILogoSVG } from "@/components/icons/cyplanai";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { useAppState } from "@/providers/AppState";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { useAuth } from "@/providers/Auth";

const SEARCH_HISTORY_STORAGE_KEY = "cyplanai:threadSearchHistory";
const MAX_HISTORY_ITEMS = 10;

interface ThreadListItemProps {
  thread: Thread;
  title: string;
  subtitle: string;
  timestamp?: string;
  isActive: boolean;
  onOpen: () => void;
  onDeleted: (threadId: string) => void;
  onRename: (thread: Thread, nextTitle: string) => Promise<void>;
  authToken: string | null;
  apiUrl?: string;
}

function ThreadListItem({
  thread,
  title,
  subtitle,
  timestamp,
  isActive,
  onOpen,
  onDeleted,
  onRename,
  authToken,
  apiUrl,
}: ThreadListItemProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [isRenaming, setIsRenaming] = useState(false);
  const [draftTitle, setDraftTitle] = useState(title);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!menuOpen) return;
    const handleClickOutside = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [menuOpen]);

  useEffect(() => {
    setDraftTitle(title);
  }, [title]);

  useEffect(() => {
    if (!isRenaming) return;
    const timeout = setTimeout(() => {
      inputRef.current?.focus();
      inputRef.current?.select();
    }, 10);
    return () => clearTimeout(timeout);
  }, [isRenaming]);

  const deleteThreadApi = useCallback(async () => {
    if (!authToken) {
      throw new Error("You must be signed in to delete conversations.");
    }
    const baseUrl =
      apiUrl ??
      process.env.NEXT_PUBLIC_API_URL ??
      "http://localhost:2024";
    const normalizedBaseUrl = baseUrl.endsWith("/")
      ? baseUrl.slice(0, -1)
      : baseUrl;

    const response = await fetch(`${normalizedBaseUrl}/threads/${thread.thread_id}`, {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${authToken}`,
      },
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      const message =
        payload?.detail ?? payload?.message ?? "Failed to delete conversation";
      throw new Error(message);
    }
  }, [apiUrl, authToken, thread.thread_id]);

  const triggerClass = cn(
    "group relative flex w-full items-center justify-between rounded-xl px-3 py-2 text-sm transition",
    isActive
      ? "bg-sidebar-accent text-sidebar-foreground"
      : "text-sidebar-foreground/80 hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
  );
  const relativeTime = timestamp ? formatDistanceToNow(new Date(timestamp), { addSuffix: true }) : undefined;
  const subtitleText = subtitle || relativeTime ? [subtitle, relativeTime].filter(Boolean).join(" · ") : "No messages yet";

  return (
    <div
      ref={containerRef}
      className="group relative w-full px-1"
    >
      <div className={triggerClass}>
        {isRenaming ? (
          <form
            className="flex w-full items-center gap-2"
            onSubmit={async (event) => {
              event.preventDefault();
              try {
                await onRename(thread, draftTitle.trim());
                setIsRenaming(false);
              } catch (error) {
                // onRename handles toast errors already
                console.error(error);
              }
            }}
          >
            <input
              ref={inputRef}
              value={draftTitle}
              onChange={(event) => setDraftTitle(event.target.value)}
              className="flex-1 rounded-lg border border-sidebar-border bg-sidebar-accent px-2 py-1 text-sm text-sidebar-foreground placeholder:text-muted-foreground focus:border-sidebar-ring focus:outline-none focus:ring-2 focus:ring-sidebar-ring/50"
            />
            <div className="flex items-center gap-2 text-xs font-medium">
              <button
                type="button"
                onClick={() => setIsRenaming(false)}
                className="rounded-md border border-sidebar-border px-2 py-1 text-sidebar-foreground transition hover:bg-sidebar-accent"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="rounded-md bg-primary px-2 py-1 text-primary-foreground transition hover:bg-primary/90"
              >
                Save
              </button>
            </div>
          </form>
        ) : (
          <>
            <button
              className="flex flex-1 flex-col items-start text-left"
              onClick={onOpen}
            >
              <span className="line-clamp-1 text-sm font-medium">{title}</span>
              <span className="mt-0.5 line-clamp-1 text-xs text-muted-foreground">
                {subtitleText}
              </span>
            </button>
            <button
              type="button"
              onClick={(event) => {
                event.stopPropagation();
                setMenuOpen((previous) => !previous);
              }}
              className={cn(
                "ml-2 flex h-8 w-8 items-center justify-center rounded-full text-muted-foreground opacity-0 transition hover:bg-sidebar-accent hover:text-sidebar-foreground group-hover:opacity-100 focus-visible:opacity-100",
                isActive && "text-sidebar-foreground hover:bg-sidebar-accent/80",
              )}
            >
              <MoreHorizontal className="h-4 w-4" />
            </button>
          </>
        )}
      </div>
      {menuOpen && (
        <div
          className="absolute right-4 top-[calc(100%+0.5rem)] z-40 w-48 rounded-2xl border border-border bg-popover p-1 text-sm text-popover-foreground shadow-xl backdrop-blur"
          onClick={(event) => event.stopPropagation()}
        >
          {!isRenaming && (
            <button
              className="flex w-full items-center gap-2 rounded-xl px-3 py-2 transition hover:bg-accent"
              onClick={() => {
                setMenuOpen(false);
                setIsRenaming(true);
              }}
            >
              <MessageSquare className="h-4 w-4" />
              Rename
            </button>
          )}
          <button
            className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-rose-400 transition hover:bg-rose-500/20"
            onClick={() => {
              const promise = deleteThreadApi();
              setMenuOpen(false);
              toast.promise(promise, {
                loading: "Deleting conversation…",
                success: "Conversation deleted",
                error: (error) =>
                  error instanceof Error ? error.message : "Failed to delete conversation",
              });
              promise
                .then(() => onDeleted(thread.thread_id))
                .catch(() => undefined);
            }}
          >
            🗑️ Delete
          </button>
        </div>
      )}
    </div>
  );
}

function ThreadList({
  threads,
  onThreadClick,
  onThreadDeleted,
  onThreadRenamed,
}: {
  threads: Thread[];
  onThreadClick?: (threadId: string) => void;
  onThreadDeleted: (threadId: string) => void;
  onThreadRenamed: (thread: Thread, nextTitle: string) => Promise<void>;
}) {
  const { threadId, setThreadId, apiUrl } = useAppState();
  const { token } = useAuth();

  return (
    <div className="flex h-full w-full flex-col items-start justify-start gap-2 overflow-y-auto pr-1 text-sidebar-foreground [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-sidebar-border [&::-webkit-scrollbar-track]:bg-transparent">
      {threads.map((t) => {
        const metadata = (t.metadata ?? {}) as Record<string, unknown>;
        const metadataTitle =
          (metadata?.["title"] as string | undefined) ??
          (metadata?.["auto_title"] as string | undefined);

        const fallbackMessages = Array.isArray(t.values?.messages)
          ? (t.values!.messages as Thread["values"]["messages"])
          : [];
        const lastMessage =
          fallbackMessages && fallbackMessages.length > 0
            ? fallbackMessages[fallbackMessages.length - 1]
            : undefined;

        const snippet = lastMessage ? getContentString(lastMessage.content).trim() : "";
        const timestamp =
          (metadata?.["last_message_at"] as string | undefined) ??
          (metadata?.["updated_at"] as string | undefined) ??
          (t.created_at as string | undefined);

        const itemTitle =
          metadataTitle ||
          snippet ||
          (t.thread_id.startsWith("thread_") ? `Conversation ${t.thread_id.slice(7, 13)}` : t.thread_id);

        return (
          <ThreadListItem
            key={t.thread_id}
            thread={t}
            title={itemTitle}
            subtitle={snippet}
            timestamp={timestamp}
            isActive={t.thread_id === threadId}
            onOpen={() => {
              onThreadClick?.(t.thread_id);
              if (t.thread_id === threadId) return;
              setThreadId(t.thread_id);
            }}
            onDeleted={onThreadDeleted}
            onRename={onThreadRenamed}
            authToken={token}
            apiUrl={apiUrl}
          />
        );
      })}
    </div>
  );
}

function ThreadHistoryLoading() {
  return (
    <div className="flex h-full w-full flex-col items-start justify-start gap-2 overflow-y-auto pr-1 [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-white/20 [&::-webkit-scrollbar-track]:bg-transparent">
      {Array.from({ length: 30 }).map((_, i) => (
        <Skeleton
          key={`skeleton-${i}`}
          className="h-10 w-full"
        />
      ))}
    </div>
  );
}

function getThreadTimestamp(thread: Thread): number {
  const metadata = (thread.metadata ?? {}) as Record<string, unknown>;
  const candidate =
    (metadata?.["last_message_at"] as string | undefined) ??
    (metadata?.["updated_at"] as string | undefined) ??
    (thread.created_at as string | undefined);
  const parsed = candidate ? new Date(candidate).getTime() : 0;
  return Number.isNaN(parsed) ? 0 : parsed;
}

function getGroupLabel(timestamp?: string) {
  if (!timestamp) return "Earlier";
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return "Earlier";
  const now = new Date();
  const diffDays = (now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24);
  if (diffDays < 1) return "Today";
  if (diffDays < 7) return "Previous 7 days";
  if (diffDays < 30) return "Previous 30 days";
  return new Intl.DateTimeFormat("en", {
    month: "long",
    year: "numeric",
  }).format(date);
}

function formatDateDisplay(timestamp?: string) {
  if (!timestamp) return "";
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export default function ThreadHistory() {
  const isLargeScreen = useMediaQuery("(min-width: 1024px)");
  const { user } = useAuth();
  const {
    chatHistoryOpen,
    setChatHistoryOpen,
    setThreadId,
    searchOpen,
    setSearchOpen,
    setSettingsOpen,
  } = useAppState();

  const {
    getThreads,
    threads,
    setThreads,
    threadsLoading,
    setThreadsLoading,
    renameThread,
  } = useThreads();
  const [searchQuery, setSearchQuery] = useState("");
  const [searchHistory, setSearchHistory] = useState<string[]>([]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    setThreadsLoading(true);
    getThreads()
      .then(setThreads)
      .catch(() => undefined)
      .finally(() => setThreadsLoading(false));
  }, [getThreads, setThreads, setThreadsLoading]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const stored = window.localStorage.getItem(SEARCH_HISTORY_STORAGE_KEY);
      if (!stored) return;
      const parsed = JSON.parse(stored);
      if (Array.isArray(parsed)) {
        setSearchHistory(parsed.filter((item): item is string => typeof item === "string"));
      }
    } catch {
      // ignore malformed data
    }
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(
      SEARCH_HISTORY_STORAGE_KEY,
      JSON.stringify(searchHistory.slice(0, MAX_HISTORY_ITEMS)),
    );
  }, [searchHistory]);

  useEffect(() => {
    if (!searchOpen) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setSearchOpen(false);
        setSearchQuery("");
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = originalOverflow;
    };
  }, [searchOpen]);

  const sortedThreads = useMemo(
    () => [...threads].sort((a, b) => getThreadTimestamp(b) - getThreadTimestamp(a)),
    [threads],
  );

  const normalizedQuery = searchQuery.trim().toLowerCase();
  const filteredThreads = useMemo(() => {
    if (!normalizedQuery) return sortedThreads;
    return sortedThreads.filter((thread) => {
      const metadata = (thread.metadata ?? {}) as Record<string, unknown>;
      const metadataTitle =
        (metadata?.["title"] as string | undefined) ??
        (metadata?.["auto_title"] as string | undefined) ??
        "";
      const titleMatch = metadataTitle.toLowerCase().includes(normalizedQuery);
      if (titleMatch) return true;

      if (
        typeof thread.values === "object" &&
        thread.values &&
        "messages" in thread.values &&
        Array.isArray(thread.values.messages)
      ) {
        return thread.values.messages.some((msg) => {
          const content = getContentString(msg.content).toLowerCase();
          return content.includes(normalizedQuery);
        });
      }
      return thread.thread_id.toLowerCase().includes(normalizedQuery);
    });
  }, [sortedThreads, normalizedQuery]);

  const addToSearchHistory = useCallback((term: string) => {
    const trimmed = term.trim();
    if (!trimmed) return;
    setSearchHistory((prev) => {
      const withoutDup = prev.filter((item) => item.toLowerCase() !== trimmed.toLowerCase());
      return [trimmed, ...withoutDup].slice(0, MAX_HISTORY_ITEMS);
    });
  }, []);

  const handleSearchSubmit = useCallback(() => {
    if (!searchQuery.trim()) return;
    addToSearchHistory(searchQuery);
  }, [addToSearchHistory, searchQuery]);

  const handleHistoryClick = (term: string) => {
    setSearchQuery(term);
  };

  const removeHistoryItem = (term: string) => {
    setSearchHistory((prev) => prev.filter((item) => item !== term));
  };

  const clearHistory = () => {
    setSearchHistory([]);
  };

  const closeSearch = () => {
    setSearchOpen(false);
    setSearchQuery("");
  };

  const searchResults = filteredThreads.slice(0, normalizedQuery ? 25 : 12);
  const groupedResults = searchResults.reduce<Record<string, Thread[]>>((acc, thread) => {
    const metadata = (thread.metadata ?? {}) as Record<string, unknown>;
    const timestamp =
      (metadata?.["last_message_at"] as string | undefined) ??
      (metadata?.["updated_at"] as string | undefined) ??
      (thread.created_at as string | undefined);
    const bucket = getGroupLabel(timestamp);
    acc[bucket] = acc[bucket] || [];
    acc[bucket].push(thread);
    return acc;
  }, {});

  const handleThreadDeleted = useCallback(
    (deletedId: string) => {
      setThreads((previous) => previous.filter((thread) => thread.thread_id !== deletedId));
      setThreadId((current) => (current === deletedId ? null : current));
    },
    [setThreadId, setThreads],
  );

  const handleThreadRenamed = useCallback(
    async (thread: Thread, nextTitle: string) => {
      const trimmed = nextTitle.trim();
      try {
        await renameThread(thread.thread_id, trimmed.length > 0 ? trimmed : null);
        toast.success("Conversation renamed");
      } catch (error) {
        toast.error("Unable to rename conversation", {
          description: error instanceof Error ? error.message : String(error),
        });
      }
    },
    [renameThread],
  );

  const overlay =
    searchOpen && typeof document !== "undefined"
      ? createPortal(
          <div className="fixed inset-0 z-[70] flex items-start justify-center bg-background/80 backdrop-blur-sm px-4 py-16">
            <div className="w-full max-w-3xl rounded-3xl border border-border bg-card text-card-foreground shadow-2xl">
              <div className="flex items-center gap-3 border-b border-border px-6 py-5">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    value={searchQuery}
                    onChange={(event) => setSearchQuery(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") {
                        event.preventDefault();
                        handleSearchSubmit();
                      }
                    }}
                    autoFocus
                    placeholder="Search conversations…"
                    className="h-12 rounded-xl pl-10 pr-24 text-base"
                  />
                  {searchQuery && (
                    <Button
                      size="sm"
                      variant="ghost"
                      className="absolute right-2 top-1/2 h-8 -translate-y-1/2 px-2 text-xs"
                      onClick={() => setSearchQuery("")}
                    >
                      Clear
                    </Button>
                  )}
                </div>
                <Button
                  variant="ghost"
                  onClick={closeSearch}
                >
                  <X className="h-5 w-5" />
                </Button>
              </div>
              <div className="max-h-[60vh] overflow-y-auto px-6 py-5">
                <button
                  className="mb-4 flex w-full items-center gap-3 rounded-2xl border border-border bg-secondary px-4 py-3 text-left text-foreground transition hover:bg-accent"
                  onClick={() => {
                    addToSearchHistory("New conversation");
                    closeSearch();
                    setThreadId(null);
                  }}
                >
                  <span className="flex h-9 w-9 items-center justify-center rounded-full bg-muted">
                    <Plus className="h-4 w-4" />
                  </span>
                  <span className="text-base font-medium">Start a new conversation</span>
                </button>

                {searchHistory.length > 0 && !normalizedQuery && (
                  <div className="mb-6">
                    <div className="mb-2 flex items-center justify-between text-xs uppercase tracking-wider text-muted-foreground">
                      <span className="inline-flex items-center gap-2">
                        <History className="h-3.5 w-3.5" />
                        Recent searches
                      </span>
                      <button
                        className="text-muted-foreground transition hover:text-foreground"
                        onClick={clearHistory}
                      >
                        Clear
                      </button>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {searchHistory.map((item) => (
                        <div
                          key={item}
                          className="group flex items-center gap-1 rounded-full bg-secondary px-3 py-1 text-sm"
                        >
                          <button
                            className="text-foreground transition hover:text-foreground/80"
                            onClick={() => handleHistoryClick(item)}
                          >
                            {item}
                          </button>
                          <button
                            className="text-muted-foreground transition hover:text-foreground"
                            aria-label={`Remove ${item}`}
                            onClick={() => removeHistoryItem(item)}
                          >
                            <X className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {searchResults.length === 0 ? (
                  <div className="flex items-center justify-center rounded-2xl border border-border bg-secondary py-16 text-sm text-muted-foreground">
                    {normalizedQuery
                      ? "No conversations match your search yet."
                      : "Start chatting to build your history."}
                  </div>
                ) : (
                  Object.entries(groupedResults).map(([group, groupThreads]) => (
                    <div key={group} className="mb-6 last:mb-0">
                      <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                        {group}
                      </div>
                      <div className="space-y-2">
                        {groupThreads.map((thread) => {
                          const metadata = (thread.metadata ?? {}) as Record<string, unknown>;
                          const effectiveTitle =
                            (metadata?.["title"] as string | undefined) ??
                            (metadata?.["auto_title"] as string | undefined) ??
                            getContentString(
                              Array.isArray(thread.values?.messages) &&
                                thread.values.messages.length > 0
                                ? thread.values.messages[0].content
                                : [],
                            ) ||
                            "Untitled conversation";
                          const timestamp =
                            (metadata?.["last_message_at"] as string | undefined) ??
                            (metadata?.["updated_at"] as string | undefined) ??
                            (thread.created_at as string | undefined);

                          return (
                            <button
                              key={thread.thread_id}
                              className="flex w-full items-center justify-between rounded-2xl border border-border bg-secondary px-4 py-3 text-left transition hover:border-border/80 hover:bg-accent"
                              onClick={() => {
                                addToSearchHistory(searchQuery || effectiveTitle);
                                setThreadId(thread.thread_id);
                                closeSearch();
                              }}
                            >
                              <span className="flex items-center gap-3 text-sm text-foreground">
                                <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-muted">
                                  <MessageSquare className="h-4 w-4" />
                                </span>
                                <span className="flex flex-col">
                                  <span className="font-medium">{effectiveTitle}</span>
                                  {timestamp && (
                                    <span className="text-xs text-muted-foreground">
                                      {formatDateDisplay(timestamp)}
                                    </span>
                                  )}
                                </span>
                              </span>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>,
          document.body,
        )
      : null;

  return (
    <>
      {overlay}
      {/* Large screen sidebar content - container is provided by parent */}
      <div className="hidden h-full w-full flex-col text-sidebar-foreground lg:flex">
        <div className="flex items-center justify-between px-4 pt-4 pb-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-sidebar-accent text-sidebar-foreground">
            <CyPlanAILogoSVG width={24} height={24} />
          </div>
          <Button
            className="h-9 w-9 rounded-full border border-sidebar-border bg-sidebar-accent text-sidebar-foreground hover:bg-sidebar-accent/80"
            variant="ghost"
            onClick={() => setChatHistoryOpen((p) => !p)}
          >
            {chatHistoryOpen ? (
              <PanelRightOpen className="size-5" />
            ) : (
              <PanelRightClose className="size-5" />
            )}
          </Button>
        </div>
        <div className="px-4 pb-4">
          <Button
            className="w-full justify-start gap-2 rounded-xl border border-sidebar-border bg-sidebar-accent text-left text-sidebar-foreground hover:bg-sidebar-accent/80"
            variant="outline"
            onClick={() => {
              setSearchQuery("");
              setSearchOpen(true);
            }}
          >
            <Search className="h-4 w-4" />
            <span>Search conversations</span>
          </Button>
          <p className="mt-3 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            Recent
          </p>
        </div>

        <div className="flex-1 overflow-hidden px-3 pb-4">
          {threadsLoading ? (
            <ThreadHistoryLoading />
          ) : sortedThreads.length > 0 ? (
            <ThreadList
              threads={sortedThreads}
              onThreadDeleted={handleThreadDeleted}
              onThreadRenamed={handleThreadRenamed}
            />
          ) : (
            <div className="flex h-full items-center justify-center px-2 text-center text-sm text-muted-foreground">
              You haven't started a conversation yet. Start chatting to see it here.
            </div>
          )}
        </div>
        {/* Bottom section - ChatGPT style user profile */}
        <div className="border-t border-sidebar-border p-3">
          <button
            className="flex h-8 w-full items-center gap-3 rounded-xl px-3 text-left transition hover:bg-sidebar-accent"
            onClick={() => setSettingsOpen(true)}
          >
            <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-teal-700 text-xs font-semibold text-white">
              {user?.name?.slice(0, 2).toUpperCase() ?? "U"}
            </div>
            <div className="flex flex-1 flex-col min-w-0">
              <span className="text-sm font-medium truncate">{user?.name || "User"}</span>
              <span className="text-xs text-muted-foreground truncate">@{user?.username || "user"}</span>
            </div>
            <Settings className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
          </button>
        </div>
      </div>
      {/* Small screen: sheet/drawer */}
      <div className="lg:hidden">
        <Sheet
          open={!!chatHistoryOpen && !isLargeScreen}
          onOpenChange={(open) => {
            if (isLargeScreen) return;
            setChatHistoryOpen(open);
          }}
        >
          <SheetContent
            side="left"
            className="flex flex-col lg:hidden"
          >
            <SheetHeader>
              <SheetTitle>Thread History</SheetTitle>
            </SheetHeader>
            <div className="mt-4 w-full">
              <ThreadList
                threads={sortedThreads}
                onThreadDeleted={handleThreadDeleted}
                onThreadRenamed={handleThreadRenamed}
                onThreadClick={(id) => {
                  setThreadId(id);
                  setChatHistoryOpen((o) => !o);
                }}
              />
            </div>
            <div className="mt-4 w-full">
              <Button
                className="w-full justify-start gap-2"
                variant="outline"
                onClick={() => {
                  setSearchQuery("");
                  setSearchOpen(true);
                }}
              >
                <Search className="h-4 w-4" />
                <span>Search conversations</span>
              </Button>
            </div>
            <div className="mt-2 w-full">
              <Button
                className="w-full justify-start gap-2"
                variant="outline"
                onClick={() => setSettingsOpen(true)}
              >
                <Settings className="h-4 w-4" />
                <span>Settings</span>
              </Button>
            </div>
          </SheetContent>
        </Sheet>
      </div>
    </>
  );
}
