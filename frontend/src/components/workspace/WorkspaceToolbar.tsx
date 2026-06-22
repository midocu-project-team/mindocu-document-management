import { useEffect, useRef, useState } from 'react';
import { ChevronDown, MessageCircle, PenLine, MousePointer, Folders } from 'lucide-react';
import type { WorkspaceDocument } from '@/types/document';

type WorkspaceToolbarProps = {
  activeTool: 'select' | 'pen' | 'comment';
  onToolChange: (tool: 'select' | 'pen' | 'comment') => void;
  documents: WorkspaceDocument[];
  selectedDocumentId: string;
  onSelectDocument: (documentId: string) => void;
  currentPage: number;
  pageCount: number;
  zoom: number;
  onZoomOut: () => void;
  onZoomIn: () => void;
};

const editTools = [
  { id: 'select' as const, icon: MousePointer, label: 'Auswählen' },
  { id: 'pen' as const, icon: PenLine, label: 'Bearbeiten' },
  { id: 'comment' as const, icon: MessageCircle, label: 'Kommentar' },
];

export function WorkspaceToolbar({
  activeTool,
  onToolChange,
  documents,
  selectedDocumentId,
  onSelectDocument,
}: WorkspaceToolbarProps) {
  const [isDocumentMenuOpen, setIsDocumentMenuOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement | null>(null);

  const selectedDocument =
    documents.find((document) => document.id === selectedDocumentId) ?? documents[0];

  useEffect(() => {
    if (!isDocumentMenuOpen) {
      return undefined;
    }

    const handlePointerDown = (event: MouseEvent) => {
      if (!dropdownRef.current?.contains(event.target as Node)) {
        setIsDocumentMenuOpen(false);
      }
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsDocumentMenuOpen(false);
      }
    };

    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleEscape);

    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [isDocumentMenuOpen]);

  const handleSelectDocument = (documentId: string) => {
    onSelectDocument(documentId);
    setIsDocumentMenuOpen(false);
  };

  return (
    <div
      className="mindocu-toolbar mindocu-toolbar--workspace"
      role="toolbar"
      aria-label="Werkzeuge und Ansicht"
    >
      <div className="mindocu-toolbar-group">
        {editTools.map(({ id, icon: Icon, label }) => (
          <button
            key={id}
            type="button"
            className={`mindocu-toolbar-button${activeTool === id ? ' is-active' : ''}`}
            onClick={() => onToolChange(id)}
            aria-pressed={activeTool === id}
            aria-label={label}
          >
            <Icon size={17} />
          </button>
        ))}
      </div>

      <div className="mindocu-toolbar-group mindocu-toolbar-group--divider">
        <div className="mindocu-toolbar-dropdown" ref={dropdownRef}>
          <button
            type="button"
            className={`mindocu-toolbar-pill${isDocumentMenuOpen ? ' is-open' : ''}`}
            onClick={() => setIsDocumentMenuOpen((open) => !open)}
            aria-haspopup="menu"
            aria-expanded={isDocumentMenuOpen}
            aria-label="PDF auswählen"
          >
            <span>{selectedDocument?.label ?? 'Dokument'}</span>
            <Folders size={15} />
            <ChevronDown size={15} className={isDocumentMenuOpen ? 'is-rotated' : undefined} />
          </button>

          {isDocumentMenuOpen ? (
            <div
              className="mindocu-toolbar-dropdown-menu"
              role="menu"
              aria-label="Hochgeladene PDFs"
            >
              {documents.map((document) => {
                const isSelected = document.id === selectedDocumentId;

                return (
                  <button
                    key={document.id}
                    type="button"
                    role="menuitemradio"
                    className={`mindocu-toolbar-dropdown-item${isSelected ? ' is-active' : ''}`}
                    aria-checked={isSelected}
                    onClick={() => handleSelectDocument(document.id)}
                  >
                    <span className="mindocu-toolbar-dropdown-item-label">{document.label}</span>
                    <span className="mindocu-toolbar-dropdown-item-meta">
                      {document.segments.length} Segmente
                    </span>
                  </button>
                );
              })}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export default WorkspaceToolbar;
