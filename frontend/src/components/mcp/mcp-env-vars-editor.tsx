"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Plus, X, KeyRound } from "lucide-react";

interface McpEnvVarsEditorProps {
  value: string[];
  onChange: (vars: string[]) => void;
  disabled?: boolean;
}

export function McpEnvVarsEditor({
  value,
  onChange,
  disabled = false,
}: McpEnvVarsEditorProps) {
  const ts = useTranslations("system");
  const [input, setInput] = useState("");

  const handleAdd = () => {
    const trimmed = input.trim().toUpperCase().replace(/\s+/g, "_");
    if (!trimmed || value.includes(trimmed)) return;
    onChange([...value, trimmed]);
    setInput("");
  };

  const handleRemove = (varName: string) => {
    onChange(value.filter((v) => v !== varName));
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAdd();
    }
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm flex items-center gap-2">
          <KeyRound className="h-4 w-4" />
          {ts("requiredEnvVars")}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Input row */}
        <div className="flex items-center gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={ts("envVarPlaceholder")}
            disabled={disabled}
            className="flex-1 text-xs font-mono"
          />
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={handleAdd}
            disabled={disabled || !input.trim()}
            className="gap-1 shrink-0"
          >
            <Plus className="h-3.5 w-3.5" />
            {ts("addEnvVar")}
          </Button>
        </div>

        {/* Chips */}
        {value.length > 0 ? (
          <div className="flex flex-wrap gap-1.5">
            {value.map((varName) => (
              <Badge
                key={varName}
                variant="secondary"
                className="gap-1 pl-2 pr-1 py-1 font-mono text-xs"
              >
                {varName}
                {!disabled && (
                  <button
                    type="button"
                    onClick={() => handleRemove(varName)}
                    className="ml-0.5 rounded-full hover:bg-foreground/10 p-0.5 cursor-pointer"
                  >
                    <X className="h-3 w-3" />
                  </button>
                )}
              </Badge>
            ))}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">
            {ts("noEnvVarsRequired")}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
