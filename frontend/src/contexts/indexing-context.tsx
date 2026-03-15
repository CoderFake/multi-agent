/**
 * IndexingContext — global indexing progress tracking at tenant level.
 *
 * Runs across ALL tenant pages:
 *   1. Polls GET /indexing/tasks for active jobs
 *   2. Opens SSE per active job
 *   3. Shows toast on "completed" / "failed"
 *   4. Exposes progressMap (document_id → IndexingProgress) for knowledge page inline progress
 */
"use client";

import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import { toast } from "sonner";
import { fetchActiveTasks, syncJobStatus } from "@/lib/api/knowledge";
import { useCurrentOrg } from "@/contexts/org-context";
import { usePermissions } from "@/hooks/use-permissions";
import type { IndexingProgress, ActiveIndexJob } from "@/types/models";

const API_BASE = process.env.NEXT_PUBLIC_CMS_API_URL || "http://localhost:8002/api/v1";

interface IndexingContextValue {
  /** Map of document_id → latest progress event */
  progressMap: Map<string, IndexingProgress>;
  /** List of currently active jobs */
  activeJobs: ActiveIndexJob[];
  /** Manually refresh active jobs */
  refresh: () => void;
}

const IndexingContext = createContext<IndexingContextValue | undefined>(undefined);

export function IndexingProvider({ children }: { children: ReactNode }) {
  const { orgId } = useCurrentOrg();
  const { hasPermission } = usePermissions();
  const canViewDocs = hasPermission("document.view");
  const [activeJobs, setActiveJobs] = useState<ActiveIndexJob[]>([]);
  const [progressMap, setProgressMap] = useState<Map<string, IndexingProgress>>(new Map());
  const eventSourcesRef = useRef<Map<string, EventSource>>(new Map());
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Fetch active jobs from backend
  const loadActiveJobs = useCallback(async () => {
    if (!canViewDocs) return;
    try {
      const jobs = await fetchActiveTasks();
      setActiveJobs(jobs);
    } catch {
      // silent — don't disrupt other pages
    }
  }, [canViewDocs]);

  // Initial load + periodic poll every 15s
  useEffect(() => {
    loadActiveJobs();
    pollTimerRef.current = setInterval(loadActiveJobs, 15000);
    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    };
  }, [loadActiveJobs]);

  // Manage SSE connections based on activeJobs
  useEffect(() => {
    const activeJobIds = new Set(activeJobs.map((j) => j.id));

    // Close SSE for jobs no longer active
    for (const [jobId, es] of eventSourcesRef.current) {
      if (!activeJobIds.has(jobId)) {
        es.close();
        eventSourcesRef.current.delete(jobId);
      }
    }

    // Open SSE for new active jobs
    for (const job of activeJobs) {
      if (eventSourcesRef.current.has(job.id)) continue;

      const url = `${API_BASE}/tenant/knowledge/indexing/${job.id}/progress?org_id=${orgId}`;
      const es = new EventSource(url, { withCredentials: true });
      eventSourcesRef.current.set(job.id, es);

      es.onmessage = (event) => {
        try {
          const data: IndexingProgress = JSON.parse(event.data);
          setProgressMap((prev) => {
            const next = new Map(prev);
            next.set(data.document_id, data);
            return next;
          });

          if (data.status === "completed") {
            toast.success(`Indexing hoàn tất: ${data.message || data.document_id}`, {
              duration: 5000,
            });
            es.close();
            eventSourcesRef.current.delete(job.id);
            // Sync status back to DB
            syncJobStatus(job.id).catch(() => {});
            // Remove from active jobs
            setActiveJobs((prev) => prev.filter((j) => j.id !== job.id));
          } else if (data.status === "failed") {
            toast.error(`Indexing thất bại: ${data.error || data.message}`, {
              duration: 8000,
            });
            es.close();
            eventSourcesRef.current.delete(job.id);
            syncJobStatus(job.id).catch(() => {});
            setActiveJobs((prev) => prev.filter((j) => j.id !== job.id));
          }
        } catch {
          // ignore parse errors
        }
      };

      es.onerror = () => {
        es.close();
        eventSourcesRef.current.delete(job.id);
      };
    }

    // Cleanup on unmount
    return () => {
      for (const es of eventSourcesRef.current.values()) es.close();
      eventSourcesRef.current.clear();
    };
  }, [activeJobs]);

  const refresh = useCallback(() => {
    loadActiveJobs();
  }, [loadActiveJobs]);

  return (
    <IndexingContext.Provider value={{ progressMap, activeJobs, refresh }}>
      {children}
    </IndexingContext.Provider>
  );
}

export function useIndexing() {
  const ctx = useContext(IndexingContext);
  if (!ctx) throw new Error("useIndexing must be used within IndexingProvider");
  return ctx;
}

/**
 * Get indexing progress for a specific document.
 * Returns null if no active indexing.
 */
export function useDocumentProgress(documentId: string): IndexingProgress | null {
  const { progressMap } = useIndexing();
  return progressMap.get(documentId) ?? null;
}
