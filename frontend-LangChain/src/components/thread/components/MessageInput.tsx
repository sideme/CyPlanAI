import { FormEvent, useRef } from "react";
import { Button } from "../../ui/button";
import { Label } from "../../ui/label";
import { Plus, LoaderCircle } from "lucide-react";
import { ContentBlocksPreview } from "../ContentBlocksPreview";
import { cn } from "@/lib/utils";

interface MessageInputProps {
  input: string;
  setInput: (value: string) => void;
  contentBlocks: any[];
  handleFileUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
  removeBlock: (index: number) => void;
  handlePaste: (e: React.ClipboardEvent<HTMLTextAreaElement>) => void;
  handleSubmit: (e: FormEvent) => void;
  isLoading: boolean;
  dragOver: boolean;
  dropRef: React.RefObject<HTMLDivElement | null>;
  onStop: () => void;
}

export function MessageInput({
  input,
  setInput,
  contentBlocks,
  handleFileUpload,
  removeBlock,
  handlePaste,
  handleSubmit,
  isLoading,
  dragOver,
  dropRef,
  onStop,
}: MessageInputProps) {
  const inputTextareaRef = useRef<HTMLTextAreaElement | null>(null);

  return (
    <div
      ref={dropRef}
      className={cn(
        "relative z-10 mx-auto mb-8 w-full max-w-3xl rounded-2xl border shadow-xs transition-all",
        dragOver
          ? "border-primary border-2 border-dotted"
          : "border border-solid",
        "bg-card",
      )}
    >
      <form
        onSubmit={handleSubmit}
        className="mx-auto grid max-w-3xl grid-rows-[1fr_auto] gap-2"
      >
        <ContentBlocksPreview
          blocks={contentBlocks}
          onRemove={removeBlock}
        />
        <textarea
          ref={inputTextareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onPaste={handlePaste}
          onKeyDown={(e) => {
            if (
              e.key === "Enter" &&
              !e.shiftKey &&
              !e.metaKey &&
              !e.nativeEvent.isComposing
            ) {
              e.preventDefault();
              const el = e.target as HTMLElement | undefined;
              const form = el?.closest("form");
              form?.requestSubmit();
            }
          }}
          placeholder="Type your message..."
          className="field-sizing-content resize-none border-none bg-transparent p-3.5 pb-0 text-base text-foreground shadow-none outline-none ring-0 placeholder:text-muted-foreground focus:outline-none focus:ring-0"
        />

        <div className="flex items-center gap-6 p-2 pt-4">
          <Label
            htmlFor="file-input"
            className="flex cursor-pointer items-center gap-2 text-muted-foreground hover:text-foreground"
          >
            <Plus className="size-5" />
            <span className="text-sm">
              Upload files
            </span>
          </Label>
          <input
            id="file-input"
            type="file"
            onChange={handleFileUpload}
            multiple
            accept="application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            className="hidden"
          />
          {isLoading ? (
            <Button
              key="stop"
              onClick={onStop}
              className="ml-auto"
            >
              <LoaderCircle className="h-4 w-4 animate-spin" />
              Cancel
            </Button>
          ) : (
            <Button
              type="submit"
              className="ml-auto shadow-md transition-all"
              disabled={
                isLoading ||
                (!input.trim() && contentBlocks.length === 0)
              }
            >
              Send
            </Button>
          )}
        </div>
      </form>
    </div>
  );
}

