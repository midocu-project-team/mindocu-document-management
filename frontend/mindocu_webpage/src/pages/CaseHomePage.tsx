import { useState } from 'react';
import { Box, Snackbar, Alert } from '@mui/material';
import CasePageHeader from '../components/cases/CasePageHeader';
import CaseSection from '../components/cases/CaseSection';
import CaseCard from '../components/cases/CaseCard';
import AddCaseDialog from '../components/cases/AddCaseDialog';
import { useNavigate } from 'react-router-dom';
import { useCases, type CaseItem } from '../context/CasesContext';


export default function CaseHomePage() {
  const navigator = useNavigate();
  const { cases, addCase, renameCase, deleteCase, setCaseStatus } = useCases();
  const [addOpen, setAddOpen] = useState(false);
  const [renameTarget, setRenameTarget] = useState<CaseItem | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  function handleAddCase(name: string) {
    addCase(name);
    setAddOpen(false);
  }

  function handleRename(newName: string) {
    if (!renameTarget) return;
    renameCase(renameTarget.id, newName);
    setRenameTarget(null);
  }

  function handleDelete(id: string) {
    deleteCase(id);
  }

  function handleStatusChange(id: string, status: CaseItem['status']) {
    setCaseStatus(id, status);
  }
  function checkCaseOpening(caseId: string) {
    const caseItem = cases.find(c => c.id === caseId);
    if (!caseItem) return;
    if (caseItem.status === 'new') {
      navigator(`/pdf-review/${caseItem.id}`);
    } else if (caseItem.status === 'processing') {
        setNotice('Dieser Fall befindet sich noch in Verarbeitung und kann derzeit nicht geöffnet werden.');
        handleStatusChange(caseId, 'done');
    }
    else if (caseItem.status === 'done') {
      navigator(`/pdf-viewer/${caseItem.id}`);
    }

  }


  function renderCases(items: CaseItem[]) {
    return items.length > 0
      ? items.map((c) => (
          <CaseCard
            key={c.id}
            name={c.name}
            fileCount={c.fileCount}
            createdAt={c.createdAt}
            onClick={() => checkCaseOpening(c.id)}
            onRename={() => setRenameTarget(c)}
            onDelete={() => handleDelete(c.id)}
          />
        ))
      : undefined;
  }

  const newCases = cases.filter((c) => c.status === 'new');
  const processingCases = cases.filter((c) => c.status === 'processing');
  const doneCases = cases.filter((c) => c.status === 'done');

  return (
    <Box sx={{ p: 4 }}>
      <CasePageHeader title="Aktenanalyse" />

      <CaseSection
        title="Neue Fälle"
        emptyMessage="Keine neuen Fälle vorhanden"
        emptySubtext="Fügen Sie einen neuen Fall hinzu, um zu starten."
        onAdd={() => setAddOpen(true)}
        addLabel="Fall hinzufügen">
        {renderCases(newCases)}
      </CaseSection>

      <CaseSection title="In Verarbeitung" emptyMessage="Keine Dateien in Verarbeitung">
        {renderCases(processingCases)}
      </CaseSection>
      <CaseSection title="Fertige Fälle" emptyMessage="Keine fertigen Fälle verfügbar">
        {renderCases(doneCases)}
      </CaseSection>

      <AddCaseDialog
        open={addOpen}
        onClose={() => setAddOpen(false)}
        onConfirm={handleAddCase}
      />

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
        <Alert onClose={() => setNotice(null)} severity="warning" variant="filled" sx={{ borderRadius: 2 }}>
          {notice}
        </Alert>
      </Snackbar>
    </Box>
  );
}
