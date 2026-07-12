import { Plus, Trash2 } from 'lucide-react';
import type { ChatSessionSummary } from '@/api/types';

type ChatSessionsListProps = {
  sessions: ChatSessionSummary[];
  activeSessionId: string | null;
  onSelectSession: (sessionId: string) => void;
  onCreateSession: () => void;
  onDeleteSession: (sessionId: string) => void;
  isCreating: boolean;
};

const SESSION_TITLE_FALLBACK = 'Neue Unterhaltung';

function formatSessionDate(iso: string): string {
  return new Date(iso).toLocaleString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/** The "Chat Sessions" tab: past conversations for the active document + "neue Unterhaltung". */
export function ChatSessionsList({
  sessions,
  activeSessionId,
  onSelectSession,
  onCreateSession,
  onDeleteSession,
  isCreating,
}: ChatSessionsListProps) {
  return (
    <div className="mindocu-chat-panel">
      <button
        type="button"
        className="mindocu-chat-new-session"
        onClick={onCreateSession}
        disabled={isCreating}
      >
        <Plus size={16} style={{ verticalAlign: '-3px', marginRight: 6 }} />
        Neue Unterhaltung
      </button>

      {sessions.length === 0 ? (
        <div className="mindocu-empty-state">
          <div className="mindocu-empty-state-title">Noch keine Unterhaltungen</div>
          <p>Starte eine neue Unterhaltung, um Fragen zu diesem Dokument zu stellen.</p>
        </div>
      ) : (
        <div className="mindocu-chat-sessions-list">
          {sessions.map((session) => (
            <div key={session.session_id} className="mindocu-chat-session-row">
              <button
                type="button"
                className={`mindocu-segment-card${session.session_id === activeSessionId ? ' is-active' : ''}`}
                onClick={() => onSelectSession(session.session_id)}
              >
                <div className="mindocu-segment-card-title">
                  {session.title ?? SESSION_TITLE_FALLBACK}
                </div>
                <div className="mindocu-segment-card-meta">
                  <span>{formatSessionDate(session.created_at)}</span>
                </div>
              </button>
              <button
                type="button"
                className="mindocu-chat-session-delete"
                aria-label="Unterhaltung löschen"
                onClick={() => onDeleteSession(session.session_id)}
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
