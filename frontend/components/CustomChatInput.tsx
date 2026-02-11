"use client";

import React, { useRef, useState, useMemo, useCallback } from "react";
import { useChatContext } from "@copilotkit/react-ui";
import type { InputProps } from "@copilotkit/react-ui";
import { Plus, FileText, Search } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Context for sharing research mode + chat interaction state between page and custom Input.
 */
export const ResearchModeContext = React.createContext<{
  researchMode: boolean;
  setResearchMode: (v: boolean) => void;
  hasInteracted: boolean;
  setHasInteracted: (v: boolean) => void;
}>({
  researchMode: true,
  setResearchMode: () => {},
  hasInteracted: false,
  setHasInteracted: () => {},
});

export function useResearchMode() {
  return React.useContext(ResearchModeContext);
}

const MAX_ROWS = 6;

/**
 * Custom CopilotChat Input with "+" tools menu (Select file, Research toggle).
 * Uses the same CopilotKit CSS classes for consistent styling.
 */
export const CustomChatInput: React.FC<InputProps> = ({
  inProgress,
  onSend,
  chatReady = false,
  onStop,
  onUpload,
  hideStopButton = false,
}) => {
  const context = useChatContext();
  const { researchMode, setResearchMode, setHasInteracted } = useResearchMode();

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [text, setText] = useState("");
  const [showToolsMenu, setShowToolsMenu] = useState(false);
  const [isComposing, setIsComposing] = useState(false);

  const isInProgress = inProgress;
  const canSend = !isInProgress && text.trim().length > 0;
  const canStop = isInProgress && !hideStopButton;
  const sendDisabled = !canSend && !canStop;

  const { buttonIcon, buttonAlt } = useMemo(() => {
    if (!chatReady) return { buttonIcon: context.icons.spinnerIcon, buttonAlt: "Loading" };
    return isInProgress && !hideStopButton
      ? { buttonIcon: context.icons.stopIcon, buttonAlt: "Stop" }
      : { buttonIcon: context.icons.sendIcon, buttonAlt: "Send" };
  }, [isInProgress, chatReady, hideStopButton, context.icons]);

  const send = useCallback(() => {
    if (isInProgress || !text.trim()) return;
    setHasInteracted(true);
    onSend(text);
    setText("");
    textareaRef.current?.focus();
  }, [isInProgress, text, onSend, setHasInteracted]);

  const handleDivClick = (event: React.MouseEvent<HTMLDivElement>) => {
    const target = event.target as HTMLElement;
    if (target.closest("button")) return;
    if (target.tagName === "TEXTAREA") return;
    textareaRef.current?.focus();
  };

  // Auto-resize textarea
  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
    const el = e.target;
    el.style.height = "auto";
    const lineHeight = 24;
    const maxHeight = lineHeight * MAX_ROWS;
    el.style.height = `${Math.min(el.scrollHeight, maxHeight)}px`;
  };

  return (
    <div className="copilotKitInputContainer">
      <div className="copilotKitInput" onClick={handleDivClick}>
        <textarea
          ref={textareaRef}
          placeholder={context.labels.placeholder}
          autoFocus={false}
          rows={1}
          value={text}
          onChange={handleTextChange}
          onCompositionStart={() => setIsComposing(true)}
          onCompositionEnd={() => setIsComposing(false)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey && !isComposing) {
              event.preventDefault();
              if (canSend) send();
            }
          }}
          style={{ overflow: "auto", resize: "none" }}
        />
        <div className="copilotKitInputControls">
          <div className="relative">
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowToolsMenu(!showToolsMenu);
              }}
              className={cn(
                "w-6 h-6 flex items-center justify-center rounded-full",
                "border-0 bg-transparent cursor-pointer p-0",
                "transition-all duration-200",
                showToolsMenu
                  ? "text-[#6766FC] rotate-45 scale-110"
                  : "text-gray-400 hover:text-gray-600 hover:scale-110"
              )}
              title="Tools"
              type="button"
            >
              <Plus className="w-[18px] h-[18px]" />
            </button>

            {/* Tools popover */}
            {showToolsMenu && (
              <>
                {/* Backdrop */}
                <div
                  className="fixed inset-0 z-10"
                  onClick={() => setShowToolsMenu(false)}
                />
                <div className="absolute left-0 bottom-[calc(100%+8px)] z-30 w-48 bg-white rounded-xl shadow-lg border border-gray-200 py-1">
                  {/* Select file */}
                  <button
                    type="button"
                    className="flex items-center gap-2.5 w-full px-3 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                    onClick={() => {
                      // TODO: file picker
                      setShowToolsMenu(false);
                    }}
                  >
                    <FileText className="w-4 h-4 text-gray-400" />
                    Select file
                  </button>

                  <div className="h-px bg-gray-100 mx-2" />

                  {/* Research toggle */}
                  <button
                    type="button"
                    className="flex items-center justify-between w-full px-3 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                    onClick={() => setResearchMode(!researchMode)}
                  >
                    <div className="flex items-center gap-2.5">
                      <Search className="w-4 h-4 text-gray-400" />
                      Research
                    </div>
                    {/* Toggle switch */}
                    <div
                      className={cn(
                        "w-8 h-[18px] rounded-full transition-colors duration-200 relative flex-shrink-0",
                        researchMode ? "bg-[#6766FC]" : "bg-gray-300"
                      )}
                    >
                      <div
                        className={cn(
                          "absolute top-[2px] w-[14px] h-[14px] rounded-full bg-white shadow-sm transition-transform duration-200",
                          researchMode ? "translate-x-[16px]" : "translate-x-[2px]"
                        )}
                      />
                    </div>
                  </button>
                </div>
              </>
            )}
          </div>

          <div style={{ flexGrow: 1 }} />

          {/* Send / Stop button */}
          <button
            disabled={sendDisabled}
            onClick={isInProgress && !hideStopButton ? onStop : send}
            data-copilotkit-in-progress={inProgress}
            className="copilotKitInputControlButton"
            aria-label={buttonAlt}
            type="button"
          >
            {buttonIcon}
          </button>
        </div>
      </div>
    </div>
  );
};
