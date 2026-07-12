import { useEffect, useRef, useState } from 'react';
import { Send } from 'lucide-react';
import type { ChatMessage, ChatSessionDetail } from '@/api/types';
import { ReferenceText } from '@/components/workspace/ReferenceText';

type ChatPanelProps = {
  /** The open session, or `undefined` if none is selected yet. */
  session: ChatSessionDetail | undefined;
  onSend: (question: string) => void;
  /** True while a question is in flight -- can be slow on a local model. */
  isSending: boolean;
  /** Which message's references are driving the PDF highlight, if any. */
  activeChatMessageId: number | null;
  activeReferenceIndex: number | null;
  onReferenceClick: (messageId: number, index: number) => void;
  onStartNewSession: () => void;
  isStartingSession: boolean;
};

/**
 * The "Chat" tab: the open session's messages (assistant answers rendered as
 * clickable, grounded references via ReferenceText -- same mechanism as the
 * segment summary) plus the question composer.
 */
export function ChatPanel({
  session,
  onSend,
  isSending,
  activeChatMessageId,
  activeReferenceIndex,
  onReferenceClick,
  onStartNewSession,
  isStartingSession,
}: ChatPanelProps) {
  const [question, setQuestion] = useState('');
  const messagesRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesRef.current?.scrollTo({ top: messagesRef.current.scrollHeight });
  }, [session?.messages.length]);

  const handleSubmit = () => {
    const trimmed = question.trim();
    if (!trimmed || isSending) {
      return;
    }
    onSend(trimmed);
    setQuestion('');
  };

  if (!session) {
    return (
      <div className="mindocu-chat-panel">
        <div className="mindocu-empty-state">
          <div className="mindocu-empty-state-title">Chat</div>
          <p>
            Stelle Fragen zu diesem Dokument — Antworten werden mit Textstellen aus der Akte
            belegt und sind anklickbar.
          </p>
        </div>
        <button
          type="button"
          className="mindocu-chat-new-session"
          onClick={onStartNewSession}
          disabled={isStartingSession}
        >
          Neue Unterhaltung starten
        </button>
      </div>
    );
  }

  return (
    <div className="mindocu-chat-panel">
      <div className="mindocu-chat-messages" ref={messagesRef}>
        {session.messages.map((message) => (
          <ChatMessageBubble
            key={message.message_id}
            message={message}
            activeReferenceIndex={
              message.message_id === activeChatMessageId ? activeReferenceIndex : null
            }
            onReferenceClick={(index) => onReferenceClick(message.message_id, index)}
          />
        ))}
        {isSending ? <p className="mindocu-chat-pending">Antwort wird generiert …</p> : null}
      </div>

      <div className="mindocu-chat-composer">
        <textarea
          className="mindocu-chat-textarea"
          placeholder="Frage zum Dokument stellen …"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault();
              handleSubmit();
            }
          }}
          disabled={isSending}
          rows={1}
        />
        <button
          type="button"
          className="mindocu-chat-send"
          onClick={handleSubmit}
          disabled={isSending || question.trim().length === 0}
          aria-label="Frage senden"
        >
          <Send size={16} />
        </button>
      </div>
    </div>
  );
}

function ChatMessageBubble({
  message,
  activeReferenceIndex,
  onReferenceClick,
}: {
  message: ChatMessage;
  activeReferenceIndex: number | null;
  onReferenceClick: (index: number) => void;
}) {
  if (message.role === 'user') {
    return <div className="mindocu-chat-message mindocu-chat-message--user">{message.text}</div>;
  }

  return (
    <div className="mindocu-chat-message mindocu-chat-message--assistant">
      <ReferenceText
        references={message.references}
        activeReferenceIndex={activeReferenceIndex}
        onReferenceClick={onReferenceClick}
        fallback={message.text}
      />
    </div>
  );
}
