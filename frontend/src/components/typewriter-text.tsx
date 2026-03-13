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

/** Renders text with line break support */
function renderWithBreaks(text: string): React.ReactNode {
  const lines = text.split("\n");
  return lines.map((line, lineIndex) => (
    <span key={lineIndex}>
      {lineIndex > 0 && <br />}
      {line}
    </span>
  ));
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
      {renderWithBreaks(displayedText)}
      {cursor && <span className="animate-pulse ml-0.5 inline-block">{cursor}</span>}
    </span>
  );
}
