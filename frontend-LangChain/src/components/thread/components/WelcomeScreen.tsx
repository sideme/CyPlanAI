import { Button } from "../../ui/button";
import { Label } from "../../ui/label";
import { Plus, LoaderCircle } from "lucide-react";
import { ContentBlocksPreview } from "../ContentBlocksPreview";
import { FormEvent } from "react";

interface QuickPrompt {
  title: string;
  description: string;
  value: string;
}

interface WelcomeScreenProps {
  user: { name?: string; username?: string } | null;
  input: string;
  setInput: (value: string) => void;
  contentBlocks: any[];
  handleFileUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
  removeBlock: (index: number) => void;
  handleSubmit: (e: FormEvent) => void;
  isLoading: boolean;
  quickPrompts: QuickPrompt[];
  onQuickPrompt: (value: string) => void;
}

export function WelcomeScreen({
  user,
  input,
  setInput,
  contentBlocks,
  handleFileUpload,
  removeBlock,
  handleSubmit,
  isLoading,
  quickPrompts,
  onQuickPrompt,
}: WelcomeScreenProps) {
  return (
    <div className="flex w-full h-full flex-col items-center justify-center gap-6 py-8 overflow-hidden">
      <div className="flex flex-col items-center gap-3 flex-shrink-0">
        <span className="rounded-full border border-border px-4 py-1 text-xs uppercase tracking-[0.35em] text-muted-foreground">
          Welcome back
          {user?.name || user?.username
            ? `, ${user?.name || user?.username}`
            : ""}
        </span>
        <h2 className="text-3xl font-semibold text-foreground md:text-4xl">
          What&apos;s on the agenda today?
        </h2>
        <p className="max-w-2xl text-sm text-muted-foreground md:text-base px-4">
          Ask CyPlanAI for cybersecurity strategies, explore frameworks, or pick up a saved conversation from the sidebar.
        </p>
      </div>
      <div className="relative w-full max-w-2xl flex-shrink-0 px-4">
        <form
          onSubmit={handleSubmit}
          className="flex items-center gap-4 rounded-[28px] border border-border bg-card px-6 py-4 text-left text-lg shadow-lg backdrop-blur"
        >
          <Label
            htmlFor="welcome-file-input"
            className="flex cursor-pointer items-center text-muted-foreground hover:text-foreground flex-shrink-0"
          >
            <Plus className="h-5 w-5" />
          </Label>
          <input
            id="welcome-file-input"
            type="file"
            onChange={handleFileUpload}
            multiple
            accept="application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            className="hidden"
          />
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask anything"
            className="flex-1 bg-transparent border-none outline-none text-base text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-0"
            autoFocus
          />
          <Button
            type="submit"
            size="sm"
            className="flex-shrink-0"
            disabled={isLoading || (!input.trim() && contentBlocks.length === 0)}
          >
            {isLoading ? (
              <LoaderCircle className="h-4 w-4 animate-spin" />
            ) : (
              "Send"
            )}
          </Button>
        </form>
        {contentBlocks.length > 0 && (
          <div className="mt-2">
            <ContentBlocksPreview
              blocks={contentBlocks}
              onRemove={removeBlock}
            />
          </div>
        )}
      </div>
      <div className="grid w-full max-w-2xl gap-2 md:grid-cols-2 flex-shrink-0 px-4 overflow-y-auto min-h-0">
        {quickPrompts.map((prompt) => (
          <button
            key={prompt.title}
            className="group flex w-full flex-col items-start gap-2 rounded-2xl border border-border bg-card p-3 text-left transition hover:border-primary/30 hover:bg-accent"
            onClick={() => onQuickPrompt(prompt.value)}
          >
            <span className="text-sm font-semibold text-foreground">
              {prompt.title}
            </span>
            <span className="text-xs text-muted-foreground md:text-sm">
              {prompt.description}
            </span>
            <span className="text-xs text-muted-foreground transition group-hover:text-foreground">
              {"Try it ->"}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}

