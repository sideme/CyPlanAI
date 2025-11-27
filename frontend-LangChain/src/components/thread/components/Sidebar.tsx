import { motion } from "framer-motion";
import { CyPlanAILogoSVG } from "../../icons/cyplanai";
import { TooltipIconButton } from "../tooltip-icon-button";
import {
  PanelRightClose,
  SquarePen,
  Search,
  ShieldCheck,
} from "lucide-react";
import ThreadHistory from "../history";

interface SidebarProps {
  chatHistoryOpen: boolean;
  setChatHistoryOpen: (open: boolean) => void;
  onNewChat: () => void;
  onSearch: () => void;
  onComingSoon: () => void;
  userInitials: string;
  onProfileClick: () => void;
}

export function Sidebar({
  chatHistoryOpen,
  setChatHistoryOpen,
  onNewChat,
  onSearch,
  onComingSoon,
  userInitials,
  onProfileClick,
}: SidebarProps) {
  return (
    <motion.div
      className="relative hidden h-screen flex-shrink-0 lg:flex"
      animate={{
        width: chatHistoryOpen ? 280 : 52,
      }}
      initial={{ width: chatHistoryOpen ? 280 : 52 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
    >
      {/* Collapsed nav bar - visible when sidebar is closed */}
      <motion.div
        className="absolute inset-0 flex h-full w-[52px] flex-col items-center border-r border-border bg-sidebar text-muted-foreground"
        animate={{
          opacity: chatHistoryOpen ? 0 : 1,
          pointerEvents: chatHistoryOpen ? "none" : "auto",
        }}
        transition={{ duration: 0.15 }}
      >
        {/* Top section - matches expanded sidebar header */}
        <div className="flex flex-col items-center pt-4 pb-3">
          {/* Open sidebar - shows logo, changes to arrow on hover */}
          <TooltipIconButton
            tooltip="Open sidebar"
            className="group flex h-10 w-10 items-center justify-center rounded-2xl bg-sidebar-accent text-sidebar-foreground hover:bg-sidebar-accent/80"
            onClick={() => setChatHistoryOpen(true)}
          >
            <CyPlanAILogoSVG width={24} height={24} className="group-hover:hidden" />
            <PanelRightClose className="size-5 hidden group-hover:block" />
          </TooltipIconButton>
        </div>
        {/* Middle section - matches expanded sidebar buttons */}
        <div className="flex flex-col items-center gap-2 px-2">
          {/* New chat */}
          <TooltipIconButton
            tooltip="New chat"
            className="size-10 rounded-lg text-muted-foreground hover:bg-accent hover:text-accent-foreground"
            onClick={onNewChat}
          >
            <SquarePen className="size-5" />
          </TooltipIconButton>
          {/* Search chats */}
          <TooltipIconButton
            tooltip="Search chats ⌘K"
            className="size-10 rounded-lg text-muted-foreground hover:bg-accent hover:text-accent-foreground"
            onClick={onSearch}
          >
            <Search className="size-5" />
          </TooltipIconButton>
          {/* Explore GPTs / Projects */}
          <TooltipIconButton
            tooltip="Explore"
            className="size-10 rounded-lg text-muted-foreground hover:bg-accent hover:text-accent-foreground"
            onClick={onComingSoon}
          >
            <ShieldCheck className="size-5" />
          </TooltipIconButton>
        </div>
        {/* Spacer */}
        <div className="flex-1" />
        {/* Bottom section - matches expanded sidebar footer */}
        <div className="flex flex-col items-center border-t border-sidebar-border p-3">
          <button
            className="flex h-8 w-8 items-center justify-center rounded-full bg-teal-700 text-xs font-semibold text-white transition hover:bg-teal-600"
            onClick={onProfileClick}
            aria-label="Open profile menu"
          >
            {userInitials}
          </button>
        </div>
      </motion.div>

      {/* Expanded sidebar - visible when sidebar is open */}
      <motion.div
        className="absolute inset-0 h-full overflow-hidden border-r border-border bg-sidebar"
        style={{ width: 280 }}
        animate={{
          opacity: chatHistoryOpen ? 1 : 0,
          pointerEvents: chatHistoryOpen ? "auto" : "none",
        }}
        transition={{ duration: 0.15 }}
      >
        <div className="relative h-full" style={{ width: 280 }}>
          <ThreadHistory />
        </div>
      </motion.div>
    </motion.div>
  );
}

