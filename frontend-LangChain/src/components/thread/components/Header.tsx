import { motion } from "framer-motion";
import { Button } from "../../ui/button";
import {
  PanelRightOpen,
  PanelRightClose,
  SquarePen,
  Edit2,
  LogOut,
} from "lucide-react";
import { TooltipIconButton } from "../tooltip-icon-button";

interface HeaderProps {
  chatStarted: boolean;
  isLargeScreen: boolean;
  chatHistoryOpen: boolean;
  setChatHistoryOpen: (open: boolean | ((prev: boolean) => boolean)) => void;
  onNewChat: () => void;
  threadId: string | null;
  onRenameThread: () => void;
  user: { name?: string; username?: string } | null;
  onLogout: () => void;
}

export function Header({
  chatStarted,
  isLargeScreen,
  chatHistoryOpen,
  setChatHistoryOpen,
  onNewChat,
  threadId,
  onRenameThread,
  user,
  onLogout,
}: HeaderProps) {
  return (
    <div className="relative z-10 flex items-center justify-between gap-3 p-2">
      <div className="relative flex items-center justify-start gap-2 flex-1">
        <div className="absolute left-0 z-10">
          {!isLargeScreen && (
            <Button
              className="hover:bg-gray-100"
              variant="ghost"
              onClick={() => setChatHistoryOpen((p) => !p)}
            >
              {chatHistoryOpen ? (
                <PanelRightOpen className="size-5" />
              ) : (
                <PanelRightClose className="size-5" />
              )}
            </Button>
          )}
        </div>
        <motion.div
          className="flex items-center gap-2"
          animate={{
            // On small screens, add margin to avoid toggle button
            // On large screens, the collapsed nav bar handles spacing via flex layout
            marginLeft: !isLargeScreen && !chatHistoryOpen ? 48 : 0,
          }}
          transition={{
            type: "spring",
            stiffness: 300,
            damping: 30,
          }}
        >
          <button
            className="cursor-pointer"
            onClick={onNewChat}
          >
            <span className="text-xl font-semibold tracking-tight">
              CyPlanAI
            </span>
          </button>
        </motion.div>
      </div>

      {!chatStarted && user && (
        <div className="flex items-center gap-4">
          <TooltipIconButton
            size="lg"
            className="p-4"
            tooltip="Sign out"
            variant="ghost"
            onClick={onLogout}
          >
            <LogOut className="size-5" />
          </TooltipIconButton>
        </div>
      )}

      {chatStarted && (
        <>
          <div className="flex items-center gap-4">
            {threadId && (
              <TooltipIconButton
                size="lg"
                className="p-4"
                tooltip="Rename conversation"
                variant="ghost"
                onClick={onRenameThread}
              >
                <Edit2 className="size-5" />
              </TooltipIconButton>
            )}
            <TooltipIconButton
              size="lg"
              className="p-4"
              tooltip="New thread"
              variant="ghost"
              onClick={onNewChat}
            >
              <SquarePen className="size-5" />
            </TooltipIconButton>
            {user && (
              <TooltipIconButton
                size="lg"
                className="p-4"
                tooltip="Sign out"
                variant="ghost"
                onClick={onLogout}
              >
                <LogOut className="size-5" />
              </TooltipIconButton>
            )}
          </div>

          <div className="from-background to-background/0 absolute inset-x-0 top-full h-5 bg-gradient-to-b" />
        </>
      )}
    </div>
  );
}

