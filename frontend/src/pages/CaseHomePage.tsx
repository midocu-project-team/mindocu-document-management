import { useState } from 'react';
import { Box, Snackbar, Alert } from '@mui/material';
import CasePageHeader from '@/components/cases/CasePageHeader';
import CaseSection from '@/components/cases/CaseSection';
import CaseCard from '@/components/cases/CaseCard';
import AddCaseDialog from '@/components/cases/AddCaseDialog';
import { useNavigate } from 'react-router-dom';
import { useCases, useCreateCase, useDeleteCase, useRenameCase } from '@/api/hooks';
import type { CaseSummary } from '@/api/types';

type DisplayStatus = 'new' | 'processing' | 'done';

/**
 * The backend only aggregates to "processing"/"done"; a case with no documents
 * yet is shown as "new" (it still needs an upload) so the three homepage
 * sections keep working.
 */
function displayStatus(item: CaseSummary): DisplayStatus {
  return item.document_count === 0 ? 'new' : item.status;
}

export default function CaseHomePage() {
  const navigator = useNavigate();
  const { data: cases = [], isError } = useCases();
  const createCase = useCreateCase();
  const renameCase = useRenameCase();
  const deleteCase = useDeleteCase();

  const [addOpen, setAddOpen] = useState(false);
  const [renameTarget, setRenameTarget] = useState<CaseSummary | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  function reportError(fallback: string) {
    return (error: unknown) => setNotice(error instanceof Error ? error.message : fallback);
  }

  function handleAddCase(name: string) {
    createCase.mutate(name, { onError: reportError('Fall konnte nicht erstellt werden.') });
    setAddOpen(false);
  }

  function handleRename(newName: string) {
    if (!renameTarget) return;
    renameCase.mutate(
      { caseId: renameTarget.id, name: newName },
      { onError: reportError('Fall konnte nicht umbenannt werden.') },
    );
    setRenameTarget(null);
  }

  function handleDelete(id: string) {
    deleteCase.mutate(id, { onError: reportError('Fall konnte nicht gelöscht werden.') });
  }

  function checkCaseOpening(item: CaseSummary) {
    const status = displayStatus(item);
    if (status === 'new') {
      navigator(`/pdf-review/${item.id}`);
    } else if (status === 'processing') {
      setNotice(
        'Dieser Fall befindet sich noch in Verarbeitung und kann derzeit nicht geöffnet werden.',
      );
    } else {
      navigator(`/pdf-viewer/${item.id}`);
    }
  }

  function renderCases(items: CaseSummary[]) {
    return items.length > 0
      ? items.map((c) => (
          <CaseCard
            key={c.id}
            name={c.name}
            fileCount={c.document_count}
            createdAt={new Date(c.created_at)}
            onClick={() => checkCaseOpening(c)}
            onRename={() => setRenameTarget(c)}
            onDelete={() => handleDelete(c.id)}
          />
        ))
      : undefined;
  }

  const newCases = cases.filter((c) => displayStatus(c) === 'new');
  const processingCases = cases.filter((c) => displayStatus(c) === 'processing');
  const doneCases = cases.filter((c) => displayStatus(c) === 'done');

  return (
    <Box sx={{ p: 4 }}>
      <CasePageHeader title="Aktenanalyse" />

      {isError && (
        <Alert severity="warning" variant="outlined" sx={{ mb: 3, borderRadius: 2 }}>
          Oops! Fälle konnten nicht geladen werden.
        </Alert>
      )}

      <CaseSection
        title="Neue Fälle"
        emptyMessage="Keine neuen Fälle vorhanden"
        emptySubtext="Fügen Sie einen neuen Fall hinzu, um zu starten."
        onAdd={() => setAddOpen(true)}
        addLabel="Fall hinzufügen"
      >
        {renderCases(newCases)}
      </CaseSection>

      <CaseSection title="In Verarbeitung" emptyMessage="Keine Dateien in Verarbeitung">
        {renderCases(processingCases)}
      </CaseSection>
      <CaseSection title="Fertige Fälle" emptyMessage="Keine fertigen Fälle verfügbar">
        {renderCases(doneCases)}
      </CaseSection>

      <AddCaseDialog open={addOpen} onClose={() => setAddOpen(false)} onConfirm={handleAddCase} />

      <AddCaseDialog
        open={!!renameTarget}
        onClose={() => setRenameTarget(null)}
        onConfirm={handleRename}
        title="Umbenennen"
        confirmLabel="Umbenennen"
        initialValue={renameTarget?.name ?? ''}
      />

      <Snackbar
        open={!!notice}
        autoHideDuration={4000}
        onClose={() => setNotice(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setNotice(null)}
          severity="warning"
          variant="filled"
          sx={{ borderRadius: 2 }}
        >
          {notice}
        </Alert>
      </Snackbar>
    </Box>
  );
}
