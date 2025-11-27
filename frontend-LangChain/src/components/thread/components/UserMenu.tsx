import { createPortal } from "react-dom";
import { LogOut, Settings, ShieldCheck } from "lucide-react";

interface UserMenuProps {
  open: boolean;
  menuRef: React.RefObject<HTMLDivElement | null>;
  user: { name?: string; username?: string } | null;
  onSettings: () => void;
  onLogout: () => void;
}

export function UserMenu({
  open,
  menuRef,
  user,
  onSettings,
  onLogout,
}: UserMenuProps) {
  if (!open || typeof document === "undefined") return null;

  return createPortal(
    <div
      ref={menuRef}
      className="fixed bottom-16 left-[60px] z-[9999] w-56 rounded-2xl border border-border bg-popover p-2 text-sm text-popover-foreground shadow-2xl"
    >
      {/* User info header */}
      <div className="mb-2 flex items-center gap-3 rounded-xl px-3 py-2">
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-teal-700 text-xs font-semibold text-white">
          {user?.name?.slice(0, 2).toUpperCase() ?? "U"}
        </div>
        <div className="flex flex-col">
          <span className="text-sm font-medium">{user?.name || "User"}</span>
          <span className="text-xs text-muted-foreground">
            @{user?.username || "user"}
          </span>
        </div>
      </div>
      <div className="my-1 border-t border-border" />
      {/* Menu items */}
      <button
        className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm transition hover:bg-accent"
        onClick={onSettings}
      >
        <Settings className="h-4 w-4 text-muted-foreground" />
        Settings
      </button>
      <button
        className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm transition hover:bg-accent"
        onClick={() => {
          // Help action - can be implemented later
        }}
      >
        <ShieldCheck className="h-4 w-4 text-muted-foreground" />
        Help
      </button>
      <div className="my-1 border-t border-border" />
      <button
        className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm transition hover:bg-accent"
        onClick={onLogout}
      >
        <LogOut className="h-4 w-4 text-muted-foreground" />
        Log out
      </button>
    </div>,
    document.body
  );
}

