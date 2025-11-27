import { Button } from "../../ui/button";
import { Input } from "../../ui/input";
import { Label } from "../../ui/label";
import { Switch } from "../../ui/switch";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetFooter,
  SheetTitle,
  SheetDescription,
} from "../../ui/sheet";
import { CyPlanAILogoSVG } from "../../icons/cyplanai";
import { ArrowDown } from "lucide-react";

interface SettingsPanelProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  theme: "light" | "dark";
  themeSelection: "light" | "dark";
  setThemeSelection: (theme: "light" | "dark") => void;
  setTheme: (theme: "light" | "dark") => void;
  hideToolCalls: boolean;
  setHideToolCalls: (hide: boolean) => void;
  apiInput: string;
  setApiInput: (value: string) => void;
  assistantInput: string;
  setAssistantInput: (value: string) => void;
  onSave: () => void;
}

export function SettingsPanel({
  open,
  onOpenChange,
  theme,
  themeSelection,
  setThemeSelection,
  setTheme,
  hideToolCalls,
  setHideToolCalls,
  apiInput,
  setApiInput,
  assistantInput,
  setAssistantInput,
  onSave,
}: SettingsPanelProps) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="flex flex-col border border-border bg-card text-card-foreground shadow-2xl"
      >
        <SheetHeader className="border-b border-border pb-4">
          <SheetTitle>Settings</SheetTitle>
          <SheetDescription>
            Manage your account and app preferences
          </SheetDescription>
        </SheetHeader>

        <div className="flex-1 space-y-6 overflow-y-auto py-6">
          {/* General section */}
          <div className="space-y-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              General
            </h3>

            <div className="flex items-center justify-between rounded-xl bg-secondary px-4 py-3">
              <div className="flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted">
                  {theme === "dark" ? (
                    <span className="text-base">🌙</span>
                  ) : (
                    <span className="text-base">☀️</span>
                  )}
                </div>
                <div>
                  <p className="text-sm font-medium">Theme</p>
                  <p className="text-xs text-muted-foreground">
                    {theme === "dark" ? "Dark mode" : "Light mode"}
                  </p>
                </div>
              </div>
              <Switch
                checked={theme === "dark"}
                onCheckedChange={(checked) => {
                  const newTheme = checked ? "dark" : "light";
                  setThemeSelection(newTheme);
                  setTheme(newTheme);
                }}
              />
            </div>

            <div className="flex items-center justify-between rounded-xl bg-secondary px-4 py-3">
              <div className="flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted">
                  <span className="text-base">🔧</span>
                </div>
                <div>
                  <p className="text-sm font-medium">Hide tool calls</p>
                  <p className="text-xs text-muted-foreground">
                    Show only final responses
                  </p>
                </div>
              </div>
              <Switch
                checked={hideToolCalls}
                onCheckedChange={setHideToolCalls}
              />
            </div>
          </div>

          {/* Data controls section */}
          <div className="space-y-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Data Controls
            </h3>

            <button className="flex w-full items-center justify-between rounded-xl bg-secondary px-4 py-3 text-left transition hover:bg-accent">
              <div className="flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted">
                  <span className="text-base">🗂️</span>
                </div>
                <div>
                  <p className="text-sm font-medium">Manage conversations</p>
                  <p className="text-xs text-muted-foreground">
                    View, export or delete your data
                  </p>
                </div>
              </div>
              <ArrowDown className="h-4 w-4 -rotate-90 text-muted-foreground" />
            </button>
          </div>

          {/* Advanced section */}
          <div className="space-y-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Advanced
            </h3>

            <div className="space-y-3 rounded-xl bg-secondary p-4">
              <div className="space-y-2">
                <Label htmlFor="settings-api" className="text-sm">
                  API URL
                </Label>
                <Input
                  id="settings-api"
                  value={apiInput}
                  onChange={(event) => setApiInput(event.target.value)}
                  placeholder="http://localhost:2024"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="settings-assistant" className="text-sm">
                  Assistant ID
                </Label>
                <Input
                  id="settings-assistant"
                  value={assistantInput}
                  onChange={(event) => setAssistantInput(event.target.value)}
                  placeholder="cyplanai"
                />
              </div>
            </div>
          </div>

          {/* About section */}
          <div className="space-y-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              About
            </h3>

            <div className="rounded-xl bg-secondary px-4 py-3">
              <div className="flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-700">
                  <CyPlanAILogoSVG width={20} height={20} />
                </div>
                <div>
                  <p className="text-sm font-medium">CyPlanAI</p>
                  <p className="text-xs text-muted-foreground">
                    Version 1.0.0 · Cybersecurity Planning Assistant
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <SheetFooter className="border-t border-border pt-4">
          <Button className="w-full" onClick={onSave}>
            Save changes
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}

