import type { SummaryReference } from '@/api/types';
import { SEGMENT_SUMMARY_FALLBACK } from '@/utils/workspaceMappers';

type InnerSidebarRightProps = {
  activeTab: 'Zusammenfassung' | 'Chat' | 'Chat Sessions';
  onTabChange: (tab: 'Zusammenfassung' | 'Chat' | 'Chat Sessions') => void;
  segmentTitle: string;
  references: SummaryReference[];
  onReferenceClick: (blockIds: number[]) => void;
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

      <div className="mindocu-inner-panel mindocu-inner-panel--summary">
        {activeTab === 'Zusammenfassung' ? (
          <>
            <div className="mindocu-summary-title">{segmentTitle}</div>
            {references.length > 0 ? (
              <div className="mindocu-summary-references">
                {references.map((reference, index) => (
                  <span
                    key={index}
                    className="mindocu-reference"
                    role="button"
                    tabIndex={0}
                    onClick={() => onReferenceClick(reference.block_ids)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault();
                        onReferenceClick(reference.block_ids);
                      }
                    }}
                  >
                    {reference.text}
                  </span>
                ))}
              </div>
            ) : SEGMENT_SUMMARY_FALLBACK}
            <p className="mindocu-summary-note">
              KI generierte Zusammenfassung — nur zur Orientierung
            </p>
          </>
        ) : null}

        {activeTab === 'Chat' ? (
          <div className="mindocu-empty-state">
            <div className="mindocu-empty-state-title">Chat</div>
            <p>Hier kann später der dialogbasierte Aktenassistent eingeblendet werden.</p>
          </div>
        ) : null}

        {activeTab === 'Chat Sessions' ? (
          <div className="mindocu-empty-state">
            <div className="mindocu-empty-state-title">Chat Sessions</div>
            <p>Gespeicherte Gespräche und Abfragen erscheinen hier.</p>
          </div>
        ) : null}
      </div>
    </aside>
  );
}

export const InneSidebarRight = InnerSidebarRight;
