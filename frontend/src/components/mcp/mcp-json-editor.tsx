"use client";

import { useTranslations } from "next-intl";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { FileJson, KeyRound } from "lucide-react";

interface McpJsonEditorProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  requiresEnvVars?: boolean;
  onToggleEnvVars?: () => void;
}

export function McpJsonEditor({ value, onChange, disabled, requiresEnvVars, onToggleEnvVars }: McpJsonEditorProps) {
  const ts = useTranslations("system");

  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <FileJson className="h-4 w-4" />
            {ts("mcpConfig")}
          </CardTitle>
          {onToggleEnvVars && (
            <Button
              type="button"
              size="sm"
              variant={requiresEnvVars ? "default" : "outline"}
              onClick={onToggleEnvVars}
              className="gap-1.5 text-xs"
            >
              <KeyRound className="h-3.5 w-3.5" />
              {ts("requiredEnvVars")}
            </Button>
          )}
        </div>
        <CardDescription className="text-xs">
          {ts("mcpConfigDesc")}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          rows={20}
          className="font-mono text-xs leading-relaxed resize-none"
          placeholder={`{
            "mcpServers": {
              "server-name": {
                "command": "npx",
                "args": ["-y", "package-name"],
                "env": {}
              }
            }
          }`}
        />
      </CardContent>
    </Card>
  );
}
