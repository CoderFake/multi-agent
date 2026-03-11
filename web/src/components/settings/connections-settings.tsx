"use client";

import { useState, useEffect, useCallback } from "react";
import { Loader2Icon, GitMergeIcon } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { GoogleDriveIcon } from "@/components/ui/icons";

interface ConnectionStatus {
  connected: boolean;
  email?: string;
  url?: string;
}

interface ConnectionCardProps {
  name: string;
  icon: React.ReactNode;
  status: ConnectionStatus | null;
  isLoading: boolean;
  onConnect: () => void;
  onDisconnect: () => void;
  disabled?: boolean;
}

function ConnectionCard({
  name,
  icon,
  status,
  isLoading,
  onConnect,
  onDisconnect,
  disabled = false,
}: ConnectionCardProps) {
  const [showDisconnectDialog, setShowDisconnectDialog] = useState(false);

  const handleDisconnect = () => {
    setShowDisconnectDialog(false);
    onDisconnect();
  };

  return (
    <>
      <div className="bg-card flex items-center justify-between rounded-lg border border-border p-4">
        <div className="flex items-center gap-3">
          <div className="flex size-10 items-center justify-center rounded-lg bg-muted">{icon}</div>
          <div>
            <p className="font-medium">{name}</p>
            {isLoading ? (
              <p className="text-sm text-muted-foreground">Checking...</p>
            ) : status?.connected ? (
              <p className="text-sm text-muted-foreground">{status.email}</p>
            ) : (
              <p className="text-sm text-muted-foreground">Not connected</p>
            )}
          </div>
        </div>
        <div>
          {isLoading ? (
            <Loader2Icon className="size-4 animate-spin text-muted-foreground" />
          ) : status?.connected ? (
            <Button variant="outline" size="sm" onClick={() => setShowDisconnectDialog(true)}>
              Disconnect
            </Button>
          ) : (
            <Button variant="outline" size="sm" onClick={onConnect} disabled={disabled}>
              {disabled ? "Coming soon" : "Connect"}
            </Button>
          )}
        </div>
      </div>

      <AlertDialog open={showDisconnectDialog} onOpenChange={setShowDisconnectDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Disconnect {name}?</AlertDialogTitle>
            <AlertDialogDescription>
              You will need to reconnect to use {name} features again.
              {status?.email && (
                <span className="mt-2 block text-foreground">
                  Connected account: {status.email}
                </span>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDisconnect}>Disconnect</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}

export function ConnectionsSettings() {
  const [googleStatus, setGoogleStatus] = useState<ConnectionStatus | null>(null);
  const [isGoogleLoading, setIsGoogleLoading] = useState(true);

  const [gitlabStatus, setGitlabStatus] = useState<ConnectionStatus | null>(null);
  const [isGitlabLoading, setIsGitlabLoading] = useState(true);
  const [showGitlabDialog, setShowGitlabDialog] = useState(false);
  const [gitlabForm, setGitlabForm] = useState({
    url: "https://gitlab.com",
    username: "",
    pat: "",
  });
  const [isSavingGitlab, setIsSavingGitlab] = useState(false);

  const [redmineStatus, setRedmineStatus] = useState<ConnectionStatus | null>(null);
  const [isRedmineLoading, setIsRedmineLoading] = useState(true);
  const [showRedmineDialog, setShowRedmineDialog] = useState(false);
  const [redmineForm, setRedmineForm] = useState({
    url: "https://redmine.example.com",
    username: "",
    apiKey: "",
  });
  const [isSavingRedmine, setIsSavingRedmine] = useState(false);

  // Fetch Google Drive connection status
  const fetchGoogleStatus = useCallback(async () => {
    try {
      const response = await fetch("/api/auth/google/status");
      const data = await response.json();
      if (response.ok) {
        setGoogleStatus({
          connected: data.connected,
          email: data.email,
        });
      }
    } catch (err) {
      console.error("Failed to fetch Google status:", err);
    } finally {
      setIsGoogleLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchGoogleStatus();
  }, [fetchGoogleStatus]);

  // Connect to Google Drive
  const handleGoogleConnect = async () => {
    try {
      setIsGoogleLoading(true);
      const response = await fetch("/api/auth/google/connect");
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to initiate connection");
      }

      // Open OAuth popup
      const width = 500;
      const height = 600;
      const left = window.screenX + (window.outerWidth - width) / 2;
      const top = window.screenY + (window.outerHeight - height) / 2;

      const popup = window.open(
        data.url,
        "google-oauth",
        `width=${width},height=${height},left=${left},top=${top}`,
      );

      if (!popup) {
        throw new Error("Popup blocked. Please allow popups for this site.");
      }

      // Poll for popup close
      const pollInterval = setInterval(async () => {
        if (popup.closed) {
          clearInterval(pollInterval);
          await fetchGoogleStatus();
        }
      }, 500);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Connection failed");
      setIsGoogleLoading(false);
    }
  };

  // Disconnect from Google Drive
  const handleGoogleDisconnect = async () => {
    try {
      setIsGoogleLoading(true);
      const response = await fetch("/api/auth/google/disconnect", {
        method: "DELETE",
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || "Failed to disconnect");
      }

      setGoogleStatus({ connected: false });
      toast.success("Google Drive disconnected");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Disconnect failed");
    } finally {
      setIsGoogleLoading(false);
    }
  };

  // Fetch GitLab connection status
  const fetchGitlabStatus = useCallback(async () => {
    try {
      const response = await fetch("/api/auth/gitlab/status");
      const data = await response.json();
      if (response.ok) {
        setGitlabStatus({
          connected: data.connected,
          email: data.email,
          url: data.url,
        });
      }
    } catch (err) {
      console.error("Failed to fetch GitLab status:", err);
    } finally {
      setIsGitlabLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchGitlabStatus();
  }, [fetchGitlabStatus]);

  // Connect to GitLab
  const handleGitlabConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setIsSavingGitlab(true);
      const response = await fetch("/api/auth/gitlab/connect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(gitlabForm),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to save GitLab connection");
      }

      toast.success("GitLab connected successfully");
      setShowGitlabDialog(false);
      await fetchGitlabStatus();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Connection failed");
    } finally {
      setIsSavingGitlab(false);
    }
  };

  // Disconnect from GitLab
  const handleGitlabDisconnect = async () => {
    try {
      setIsGitlabLoading(true);
      const response = await fetch("/api/auth/gitlab/disconnect", {
        method: "DELETE",
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || "Failed to disconnect");
      }

      setGitlabStatus({ connected: false });
      setGitlabForm({ url: "https://gitlab.com", username: "", pat: "" });
      toast.success("GitLab disconnected");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Disconnect failed");
    } finally {
      setIsGitlabLoading(false);
    }
  };

  const fetchRedmineStatus = useCallback(async () => {
    try {
      const response = await fetch("/api/auth/redmine/status");
      const data = await response.json();
      if (response.ok) {
        setRedmineStatus({ connected: data.connected, email: data.email, url: data.url });
      }
    } catch (err) {
      console.error("Failed to fetch Redmine status:", err);
    } finally {
      setIsRedmineLoading(false);
    }
  }, []);

  useEffect(() => { fetchRedmineStatus(); }, [fetchRedmineStatus]);

  const handleRedmineConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setIsSavingRedmine(true);
      const response = await fetch("/api/auth/redmine/connect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(redmineForm),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Failed to save Redmine connection");
      toast.success("Redmine connected successfully");
      setShowRedmineDialog(false);
      await fetchRedmineStatus();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Connection failed");
    } finally {
      setIsSavingRedmine(false);
    }
  };

  const handleRedmineDisconnect = async () => {
    try {
      setIsRedmineLoading(true);
      const response = await fetch("/api/auth/redmine/disconnect", { method: "DELETE" });
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || "Failed to disconnect");
      }
      setRedmineStatus({ connected: false });
      setRedmineForm({ url: "https://redmine.example.com", username: "", apiKey: "" });
      toast.success("Redmine disconnected");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Disconnect failed");
    } finally {
      setIsRedmineLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-base font-medium">Connected Accounts</h3>
        <p className="text-sm text-muted-foreground">
          Manage your connections to external services
        </p>
      </div>

      <div className="space-y-3">
        <ConnectionCard
          name="Google Drive"
          icon={<GoogleDriveIcon className="size-5" />}
          status={googleStatus}
          isLoading={isGoogleLoading}
          onConnect={handleGoogleConnect}
          onDisconnect={handleGoogleDisconnect}
        />
        <ConnectionCard
          name="GitLab"
          icon={<GitMergeIcon className="size-5" />}
          status={gitlabStatus}
          isLoading={isGitlabLoading}
          onConnect={() => setShowGitlabDialog(true)}
          onDisconnect={handleGitlabDisconnect}
        />
        <ConnectionCard
          name="Redmine"
          icon={<RedmineIcon className="size-5" />}
          status={redmineStatus}
          isLoading={isRedmineLoading}
          onConnect={() => setShowRedmineDialog(true)}
          onDisconnect={handleRedmineDisconnect}
        />
      </div>

      <Dialog open={showGitlabDialog} onOpenChange={setShowGitlabDialog}>
        <DialogContent className="sm:max-w-[425px]">
          <form onSubmit={handleGitlabConnect}>
            <DialogHeader>
              <DialogTitle>Connect GitLab</DialogTitle>
              <DialogDescription>
                Enter your GitLab credentials to enable the GitLab Assistant.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="url">Organization URL</Label>
                <Input
                  id="url"
                  placeholder="https://gitlab.com"
                  value={gitlabForm.url}
                  onChange={(e) => setGitlabForm({ ...gitlabForm, url: e.target.value })}
                  required
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="username">Username</Label>
                <Input
                  id="username"
                  placeholder="e.g. johndoe"
                  value={gitlabForm.username}
                  onChange={(e) => setGitlabForm({ ...gitlabForm, username: e.target.value })}
                  required
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="pat">Personal Access Token</Label>
                <Input
                  id="pat"
                  type="password"
                  placeholder="glpat-..."
                  value={gitlabForm.pat}
                  onChange={(e) => setGitlabForm({ ...gitlabForm, pat: e.target.value })}
                  required
                />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowGitlabDialog(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={isSavingGitlab}>
                {isSavingGitlab && <Loader2Icon className="mr-2 size-4 animate-spin" />}
                Save Connection
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={showRedmineDialog} onOpenChange={setShowRedmineDialog}>
        <DialogContent className="sm:max-w-[425px]">
          <form onSubmit={handleRedmineConnect}>
            <DialogHeader>
              <DialogTitle>Connect Redmine</DialogTitle>
              <DialogDescription>
                Enter your Redmine credentials to enable the Redmine Assistant.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="redmine-url">Redmine URL</Label>
                <Input
                  id="redmine-url"
                  placeholder="https://redmine.example.com"
                  value={redmineForm.url}
                  onChange={(e) => setRedmineForm({ ...redmineForm, url: e.target.value })}
                  required
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="redmine-username">Username</Label>
                <Input
                  id="redmine-username"
                  placeholder="e.g. johndoe"
                  value={redmineForm.username}
                  onChange={(e) => setRedmineForm({ ...redmineForm, username: e.target.value })}
                  required
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="redmine-apikey">API Key</Label>
                <Input
                  id="redmine-apikey"
                  type="password"
                  placeholder="Your Redmine API key (from /my/account)"
                  value={redmineForm.apiKey}
                  onChange={(e) => setRedmineForm({ ...redmineForm, apiKey: e.target.value })}
                  required
                />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowRedmineDialog(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={isSavingRedmine}>
                {isSavingRedmine && <Loader2Icon className="mr-2 size-4 animate-spin" />}
                Save Connection
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function RedmineIcon({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" className={className} fill="currentColor">
      <path d="M50 5C25.2 5 5 25.2 5 50s20.2 45 45 45 45-20.2 45-45S74.8 5 50 5zm0 8c20.4 0 37 16.6 37 37S70.4 87 50 87 13 70.4 13 50s16.6-37 37-37zm-14 16v42h8V51h12c4.4 0 8 3.6 8 8v12h8V57c0-6.2-4.2-11.4-10-12.8V29H36z" />
    </svg>
  );
}
