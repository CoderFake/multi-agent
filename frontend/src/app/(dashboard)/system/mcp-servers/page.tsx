"use client";

import { useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import useSWR from "swr";
import type { SystemMcpServer, McpDiscoverResponse } from "@/types/models";
import {
  fetchSystemMcpServers,
  createSystemMcpServer,
  updateSystemMcpServer,
  deleteSystemMcpServer,
  discoverMcpTools,
  syncMcpTools,
  fetchMcpServerTools,
} from "@/lib/api/system";
import { PageHeader } from "@/components/shared/page-header";
import { McpJsonEditor } from "@/components/mcp/mcp-json-editor";
import { McpToolDiscoveryPanel } from "@/components/mcp/mcp-tool-discovery-panel";
import { McpServerSelector } from "@/components/mcp/mcp-server-selector";
import { McpOrgAssignModal } from "@/components/mcp/mcp-org-assign-modal";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Plus, Trash2 } from "lucide-react";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";

const DEFAULT_MCP_JSON = JSON.stringify(
  {
    mcpServers: {
      "server-name": {
        command: "npx",
        args: ["-y", "package-name"],
        env: {},
      },
    },
  },
  null,
  2,
);

export default function SystemMcpServersPage() {
  const t = useTranslations("common");
  const ts = useTranslations("system");

  // ── Server list ─────────────────────────────────────────────────────
  const { data: servers, mutate } = useSWR(
    "system-mcp-servers",
    fetchSystemMcpServers,
  );

  // ── Selected server ─────────────────────────────────────────────────
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected = servers?.find((s) => s.id === selectedId) ?? null;

  // ── JSON editor state ───────────────────────────────────────────────
  const [mcpJson, setMcpJson] = useState(DEFAULT_MCP_JSON);

  // ── Discovered tools state ──────────────────────────────────────────
  const [discoveredResults, setDiscoveredResults] = useState<McpDiscoverResponse[]>([]);
  const [discovering, setDiscovering] = useState(false);
  const [syncing, setSyncing] = useState(false);

  // ── Delete state ────────────────────────────────────────────────────
  const [deleteTarget, setDeleteTarget] = useState<SystemMcpServer | null>(null);

  // ── Required env vars toggle ───────────────────────────────────────
  const [requiresEnvVars, setRequiresEnvVars] = useState(false);

  // ── Org assign modal ───────────────────────────────────────────────
  const [orgModalOpen, setOrgModalOpen] = useState(false);

  /** When user selects a server, load its config + saved tools; click again to deselect */
  const handleSelectServer = useCallback(
    async (id: string) => {
      if (selectedId === id) {
        setSelectedId(null);
        setMcpJson(DEFAULT_MCP_JSON);
        setDiscoveredResults([]);
        setRequiresEnvVars(false);
        return;
      }
      // Select server → fill JSON + load saved tools from DB
      setSelectedId(id);
      const server = servers?.find((s) => s.id === id);
      if (server?.connection_config) {
        setMcpJson(JSON.stringify(server.connection_config, null, 2));
      } else {
        setMcpJson(DEFAULT_MCP_JSON);
      }
      setRequiresEnvVars(server?.requires_env_vars ?? false);

      try {
        const savedTools = await fetchMcpServerTools(id);
        if (savedTools.length > 0) {
          setDiscoveredResults([
            {
              server_name: server?.codename ?? server?.display_name ?? id,
              tools: savedTools.map((t) => ({
                name: t.codename,
                description: t.description,
                input_schema: t.input_schema,
              })),
              error: null,
            },
          ]);
        } else {
          setDiscoveredResults([]);
        }
      } catch {
        setDiscoveredResults([]);
      }
    },
    [servers, selectedId],
  );

  /** Save current JSON + env toggle to selected server */
  const handleSaveConfig = useCallback(async () => {
    if (!selected) return;
    try {
      const config = JSON.parse(mcpJson);
      await updateSystemMcpServer(selected.id, {
        connection_config: config,
        requires_env_vars: requiresEnvVars,
      });
      toast.success(t("updateSuccess"));
      await mutate();
    } catch {
      toast.error(t("error"));
    }
  }, [selected, mcpJson, requiresEnvVars, mutate, t]);

  /** Toggle is_public flag on selected server */
  const handleTogglePublic = useCallback(async () => {
    if (!selected) return;
    const newPublic = !selected.is_public;
    try {
      // Optimistic update: immediately reflect in SWR data
      await mutate(
        (prev) =>
          prev?.map((s) =>
            s.id === selected.id ? { ...s, is_public: newPublic } : s,
          ),
        false,
      );
      await updateSystemMcpServer(selected.id, { is_public: newPublic });
      toast.success(newPublic ? ts("mcpSetPublic") : ts("mcpSetRestricted"));
      // Revalidate from server
      await mutate();
    } catch {
      toast.error(t("error"));
      // Rollback on error
      await mutate();
    }
  }, [selected, mutate, t, ts]);

  /** Create a new server from current JSON */
  const handleCreate = useCallback(async () => {
    try {
      const config = JSON.parse(mcpJson);
      const serverNames = Object.keys(config.mcpServers ?? config);
      const codename = serverNames[0] ?? "new-mcp-server";
      const created = await createSystemMcpServer({
        codename,
        display_name: codename,
        transport: "stdio",
        connection_config: config,
        is_active: true,
      });
      toast.success(t("createSuccess"));
      await mutate();
      setSelectedId(created.id);
    } catch {
      toast.error(t("error"));
    }
  }, [mcpJson, mutate, t]);

  /** Delete selected server */
  const handleDelete = useCallback(async () => {
    if (!deleteTarget) return;
    try {
      await deleteSystemMcpServer(deleteTarget.id);
      toast.success(t("deleteSuccess"));
      if (selectedId === deleteTarget.id) {
        setSelectedId(null);
        setDiscoveredResults([]);
        setMcpJson(DEFAULT_MCP_JSON);
      }
      setDeleteTarget(null);
      mutate();
    } catch {
      toast.error(t("error"));
    }
  }, [deleteTarget, selectedId, mutate, t]);

  /** Discover tools from JSON */
  const handleDiscover = useCallback(async () => {
    setDiscovering(true);
    try {
      const config = JSON.parse(mcpJson);
      const results = await discoverMcpTools(config);
      setDiscoveredResults(results);
      const total = results.reduce((s, r) => s + r.tools.length, 0);
      toast.success(ts("toolsDiscovered", { count: total }));
    } catch {
      toast.error(ts("discoverError"));
    } finally {
      setDiscovering(false);
    }
  }, [mcpJson, ts]);

  /** Sync discovered tools to DB */
  const handleSync = useCallback(async () => {
    if (!selected) return;
    setSyncing(true);
    try {
      const config = JSON.parse(mcpJson);
      const results = await syncMcpTools(selected.id, config);
      setDiscoveredResults(results);
      toast.success(ts("toolsSynced"));
    } catch {
      toast.error(ts("discoverError"));
    } finally {
      setSyncing(false);
    }
  }, [mcpJson, selected, ts]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHeader title={ts("mcpTitle")} description={ts("mcpDesc")}>
        <div className="flex items-center gap-2">
          {selected && (
            <Button
              variant="destructive"
              size="sm"
              onClick={() => setDeleteTarget(selected)}
              className="gap-1.5"
            >
              <Trash2 className="h-3.5 w-3.5" />
              {t("delete")}
            </Button>
          )}
          <Button size="sm" onClick={handleCreate} className="gap-1.5">
            <Plus className="h-3.5 w-3.5" />
            {ts("createMcp")}
          </Button>
        </div>
      </PageHeader>

      {/* Server selector bar */}
      <McpServerSelector
        servers={servers ?? []}
        selectedId={selectedId}
        onSelect={handleSelectServer}
        onSaveConfig={handleSaveConfig}
        onAssignOrgs={() => setOrgModalOpen(true)}
      />

      {/* is_public toggle */}
      {selected && (
        <div className="flex items-center gap-3 rounded-lg border border-border/50 bg-card px-4 py-3">
          <Switch
            id="mcp-public-toggle"
            checked={selected.is_public}
            onCheckedChange={handleTogglePublic}
          />
          <div>
            <Label htmlFor="mcp-public-toggle" className="text-sm font-medium cursor-pointer">
              {ts("mcpIsPublic")}
            </Label>
            <p className="text-xs text-muted-foreground">{ts("mcpPublicDesc")}</p>
          </div>
        </div>
      )}

      {/* col6 / col6 layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: JSON Editor */}
        <div className="min-w-0">
          <McpJsonEditor
            value={mcpJson}
            onChange={setMcpJson}
            disabled={discovering || syncing}
            requiresEnvVars={selected ? requiresEnvVars : undefined}
            onToggleEnvVars={selected ? () => setRequiresEnvVars(!requiresEnvVars) : undefined}
          />
        </div>
        {/* Right: Discovered Tools */}
        <div className="min-w-0">
          <McpToolDiscoveryPanel
            results={discoveredResults}
            discovering={discovering}
            syncing={syncing}
            showSyncButton={!!selected}
            onDiscover={handleDiscover}
            onSync={handleSync}
          />
        </div>
      </div>
      {/* Delete Confirm */}
      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(o) => !o && setDeleteTarget(null)}
        title={t("deleteConfirmTitle")}
        description={t("deleteConfirmDesc")}
        onConfirm={handleDelete}
      />

      {/* Org assign modal */}
      <McpOrgAssignModal
        serverId={selectedId}
        serverName={selected?.display_name ?? selected?.codename ?? ""}
        open={orgModalOpen}
        onOpenChange={setOrgModalOpen}
      />
    </div>
  );
}
