"use client";

import { useTypewriter } from "@/hooks/use-typewriter";
import { cn } from "@/lib/utils";

interface TypewriterTextProps {
  /** Text to type out */
  text: string;
  /** Typing speed in ms (default: 50) */
  speed?: number;
  /** Initial delay before typing starts in ms (default: 0) */
  startDelay?: number;
  /** Whether to show cursor (default: true) */
  showCursor?: boolean;
  /** Additional className for the container */
  className?: string;
}

/** Renders text with Agent branding and line breaks */
function renderWithBranding(text: string): React.ReactNode {
  // Split by newlines first
  const lines = text.split("\n");

  return lines.map((line, lineIndex) => {
    const agentIndex = line.indexOf("Agent");

    let content: React.ReactNode;
    if (agentIndex === -1) {
      content = line;
    } else {
      const before = line.slice(0, agentIndex);
      const agentEnd = agentIndex + 5; // "Agent".length
      const after = line.slice(agentEnd);

      // Calculate how much of "Agent" is visible
      const visibleAgent = line.slice(agentIndex, agentEnd);

      content = (
        <>
          {before}
          {visibleAgent && <span className="font-normal">{visibleAgent}</span>}
          {after}
        </>
      );
    }

    return (
      <span key={lineIndex}>
        {lineIndex > 0 && <br />}
        {content}
      </span>
    );
  });
}

export function TypewriterText({
  text,
  speed = 50,
  startDelay = 0,
  showCursor = true,
  className,
}: TypewriterTextProps) {
  const { displayedText, cursor } = useTypewriter({
    text,
    speed,
    startDelay,
    showCursor,
  });

  return (
    <span className={cn("inline", className)}>
      {renderWithBranding(displayedText)}
      {cursor && <span className="animate-blink ml-0.5 inline-block">{cursor}</span>}
    </span>
  );
}
