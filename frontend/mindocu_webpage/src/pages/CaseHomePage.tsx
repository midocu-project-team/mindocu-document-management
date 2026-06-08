import { useState } from 'react';
import { Box } from '@mui/material';
import CasePageHeader from '../components/cases/CasePageHeader';
import CaseSection from '../components/cases/CaseSection';
import CaseCard from '../components/cases/CaseCard';
import AddCaseDialog from '../components/cases/AddCaseDialog';
import { useNavigate } from 'react-router-dom';


interface CaseItem {
  id: string;
  name: string;
  fileCount: number;
  createdAt: Date;
}

export default function CaseHomePage() {
  const navigator = useNavigate();
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [addOpen, setAddOpen] = useState(false);
  const [renameTarget, setRenameTarget] = useState<CaseItem | null>(null);

  function handleAddCase(name: string) {
    setCases((prev) => [
      ...prev,
      { id: crypto.randomUUID(), name, fileCount: 0, createdAt: new Date() },
    ]);
    setAddOpen(false);
  }

  function handleRename(newName: string) {
    if (!renameTarget) return;
    setCases((prev) =>
      prev.map((c) => (c.id === renameTarget.id ? { ...c, name: newName } : c))
    );
    setRenameTarget(null);
  }

  function handleDelete(id: string) {
    setCases((prev) => prev.filter((c) => c.id !== id));
  }

  return (
    <Box sx={{ p: 4 }}>
      <CasePageHeader title="Aktenanalyse" /> 

      <CaseSection
        title="Neue Fälle"
        emptyMessage="Keine neuen Fälle vorhanden"
        emptySubtext="Fügen Sie einen neuen Fall hinzu, um zu starten."
        onAdd={() => setAddOpen(true)}
        addLabel="Fall hinzufügen"
      >
        {cases.length > 0
          ? cases.map((c) => (
              <CaseCard
                key={c.id}
                name={c.name}
                fileCount={c.fileCount}
                createdAt={c.createdAt}
                onClick={() => navigator('/pdf-review')}
                onRename={() => setRenameTarget(c)}
                onDelete={() => handleDelete(c.id)}
              />
            ))
          : undefined}
      </CaseSection>

      <CaseSection title="In Verarbeitung" emptyMessage="Keine Dateien in Verarbeitung" />
      <CaseSection title="Fertige Fälle" emptyMessage="Keine fertigen Fälle verfügbar" />

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
    </Box>
  );
}
