import type { ChatSessionDetail, ChatSessionSummary, SummaryReference } from '@/api/types';
import { SEGMENT_SUMMARY_FALLBACK } from '@/utils/workspaceMappers';
import { ReferenceText } from '@/components/workspace/ReferenceText';
import { ChatPanel } from '@/components/workspace/ChatPanel';
import { ChatSessionsList } from '@/components/workspace/ChatSessionsList';

type InnerSidebarRightProps = {
  activeTab: 'Zusammenfassung' | 'Chat' | 'Chat Sessions';
  onTabChange: (tab: 'Zusammenfassung' | 'Chat' | 'Chat Sessions') => void;
  segmentTitle: string;
  references: SummaryReference[];
  onReferenceClick: (index: number) => void;
  // The reference whose hit bar is currently open; stays underlined until closed.
  // Shared across the summary and chat tabs -- only the currently visible one uses it.
  activeReferenceIndex: number | null;

  // Chat tab
  activeChatSession: ChatSessionDetail | undefined;
  activeChatMessageId: number | null;
  onSendChatMessage: (question: string) => void;
  isSendingChatMessage: boolean;
  onChatReferenceClick: (messageId: number, index: number) => void;

  // Chat Sessions tab
  chatSessions: ChatSessionSummary[];
  activeChatSessionId: string | null;
  onSelectChatSession: (sessionId: string) => void;
  onCreateChatSession: () => void;
  onDeleteChatSession: (sessionId: string) => void;
  isCreatingChatSession: boolean;
};

const rightTabs: Array<{ label: InnerSidebarRightProps['activeTab'] }> = [
  { label: 'Zusammenfassung' },
  { label: 'Chat' },
  { label: 'Chat Sessions' },
];

export function InnerSidebarRight({
  activeTab,
  onTabChange,
  segmentTitle,
  references,
  onReferenceClick,
  activeReferenceIndex,
  activeChatSession,
  activeChatMessageId,
  onSendChatMessage,
  isSendingChatMessage,
  onChatReferenceClick,
  chatSessions,
  activeChatSessionId,
  onSelectChatSession,
  onCreateChatSession,
  onDeleteChatSession,
  isCreatingChatSession,
}: InnerSidebarRightProps) {
  return (
    <aside className="mindocu-inner-sidebar mindocu-inner-sidebar--right">
      <div
        className="mindocu-inner-tabs mindocu-inner-tabs--compact"
        role="tablist"
        aria-label="Seitenpanel"
      >
        {rightTabs.map(({ label }) => (
          <button
            key={label}
            type="button"
            className={`mindocu-inner-tab${activeTab === label ? ' is-active' : ''}`}
            onClick={() => onTabChange(label)}
          >
            <span>{label}</span>
          </button>
        ))}
      </div>

      <div
        className={`mindocu-inner-panel${activeTab === 'Zusammenfassung' ? ' mindocu-inner-panel--summary' : ' mindocu-inner-panel--chat'}`}
      >
        {activeTab === 'Zusammenfassung' ? (
          <>
            <div className="mindocu-summary-title">{segmentTitle}</div>
            <ReferenceText
              references={references}
              activeReferenceIndex={activeReferenceIndex}
              onReferenceClick={onReferenceClick}
              fallback={SEGMENT_SUMMARY_FALLBACK}
            />
            <p className="mindocu-summary-note">
              KI generierte Zusammenfassung — nur zur Orientierung
            </p>
          </>
        ) : null}

        {activeTab === 'Chat' ? (
          <ChatPanel
            session={activeChatSession}
            onSend={onSendChatMessage}
            isSending={isSendingChatMessage}
            activeChatMessageId={activeChatMessageId}
            activeReferenceIndex={activeReferenceIndex}
            onReferenceClick={onChatReferenceClick}
            onStartNewSession={onCreateChatSession}
            isStartingSession={isCreatingChatSession}
          />
        ) : null}

        {activeTab === 'Chat Sessions' ? (
          <ChatSessionsList
            sessions={chatSessions}
            activeSessionId={activeChatSessionId}
            onSelectSession={onSelectChatSession}
            onCreateSession={onCreateChatSession}
            onDeleteSession={onDeleteChatSession}
            isCreating={isCreatingChatSession}
          />
        ) : null}
      </div>
    </aside>
  );
}

export const InneSidebarRight = InnerSidebarRight;
