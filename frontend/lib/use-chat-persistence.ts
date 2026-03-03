'use client';

import { useEffect, useRef, useCallback } from 'react';
import { useCopilotChat } from '@copilotkit/react-core';
import { api } from './api';

/**
 * Hook that automatically persists CopilotKit chat messages to the backend.
 *
 * - When the first user message is sent, creates a new session (or reuses activeSessionId).
 * - After the assistant finishes responding (isLoading false), saves the query+response pair.
 * - Calls onSessionCreated when a new session is created so the sidebar can refresh.
 */
export function useChatPersistence({
  token,
  activeSessionId,
  onSessionCreated,
}: {
  token: string;
  activeSessionId: string | null;
  onSessionCreated: (sessionId: string, title: string | null) => void;
}) {
  const { visibleMessages, isLoading } = useCopilotChat();

  // Track which messages we've already saved (by their message ID)
  const savedMessageIds = useRef<Set<string>>(new Set());
  // Track the current session ID (may differ from activeSessionId if auto-created)
  const currentSessionId = useRef<string | null>(activeSessionId);
  // Track previous isLoading state to detect transitions
  const wasLoading = useRef(false);
  // Prevent concurrent saves
  const isSaving = useRef(false);

  // Sync activeSessionId changes
  useEffect(() => {
    currentSessionId.current = activeSessionId;
    savedMessageIds.current.clear();
  }, [activeSessionId]);

  const saveMessages = useCallback(async () => {
    if (isSaving.current) return;
    if (!visibleMessages || visibleMessages.length === 0) return;

    // Find unsaved user→assistant TextMessage pairs
    const pairs: Array<{ userMsg: any; assistantMsg: any }> = [];

    for (let i = 0; i < visibleMessages.length; i++) {
      const msg = visibleMessages[i];
      if (
        msg.isTextMessage() &&
        msg.role === 'user' &&
        !savedMessageIds.current.has(msg.id) &&
        msg.content?.trim()
      ) {
        // Find the next assistant text message
        const nextMsg = visibleMessages[i + 1];
        if (
          nextMsg &&
          nextMsg.isTextMessage() &&
          nextMsg.role === 'assistant' &&
          nextMsg.content?.trim()
        ) {
          pairs.push({ userMsg: msg, assistantMsg: nextMsg });
        }
      }
    }

    if (pairs.length === 0) return;

    isSaving.current = true;
    try {
      for (const { userMsg, assistantMsg } of pairs) {
        // Skip if already saved
        if (savedMessageIds.current.has(userMsg.id)) continue;

        const result = await api.addChatMessage(
          token,
          userMsg.content,
          assistantMsg.content,
          currentSessionId.current || undefined,
        );

        // Mark as saved
        savedMessageIds.current.add(userMsg.id);

        // If a new session was created, update our ref and notify parent
        if (!currentSessionId.current && result.session_id) {
          currentSessionId.current = result.session_id;
          onSessionCreated(result.session_id, result.title);
        }
      }
    } catch (err) {
      console.error('Failed to save chat message:', err);
    } finally {
      isSaving.current = false;
    }
  }, [visibleMessages, token, onSessionCreated]);

  // Save when isLoading transitions from true → false (assistant finished responding)
  useEffect(() => {
    if (wasLoading.current && !isLoading) {
      // Small delay to ensure the last message content is fully rendered
      const timer = setTimeout(() => saveMessages(), 300);
      return () => clearTimeout(timer);
    }
    wasLoading.current = isLoading;
  }, [isLoading, saveMessages]);
}
