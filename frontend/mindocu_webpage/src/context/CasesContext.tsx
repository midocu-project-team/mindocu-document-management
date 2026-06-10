import { createContext, useContext, useState, type ReactNode } from 'react';

export type CaseStatus = 'new' | 'processing' | 'done';

export interface CaseItem {
  id: string;
  name: string;
  fileCount: number;
  createdAt: Date;
  status: CaseStatus;
}

interface CasesContextValue {
  cases: CaseItem[];
  addCase: (name: string) => void;
  renameCase: (id: string, newName: string) => void;
  deleteCase: (id: string) => void;
  setCaseStatus: (id: string, status: CaseStatus) => void;
  addFileToCase: (id: string, count?: number) => void;
  removeFileFromCase: (id: string) => void;
}

const CasesContext = createContext<CasesContextValue | null>(null);

export function CasesProvider({ children }: { children: ReactNode }) {
  const [cases, setCases] = useState<CaseItem[]>([]);

  function addCase(name: string) {
    setCases((prev) => [
      ...prev,
      { id: crypto.randomUUID(), name, fileCount: 0, createdAt: new Date(), status: 'new' },
    ]);
  }

  function renameCase(id: string, newName: string) {
    setCases((prev) => prev.map((c) => (c.id === id ? { ...c, name: newName } : c)));
  }

  function deleteCase(id: string) {
    setCases((prev) => prev.filter((c) => c.id !== id));
  }

  function setCaseStatus(id: string, status: CaseStatus) {
    setCases((prev) => prev.map((c) => (c.id === id ? { ...c, status } : c)));
  }
  function addFileToCase(id: string, count: number = 1) {
    setCases((prev) =>
      prev.map((c) => (c.id === id ? { ...c, fileCount: c.fileCount + count } : c))
    );
  }
  
  function removeFileFromCase(id: string) {
    setCases((prev) =>
      prev.map((c) => (c.id === id ? { ...c, fileCount: Math.max(0, c.fileCount - 1) } : c))
    );
  }

  return (
    <CasesContext.Provider value={{ cases, addCase, renameCase, deleteCase, setCaseStatus, addFileToCase, removeFileFromCase }}>
      {children}
    </CasesContext.Provider>
  );
}

export function useCases() {
  const ctx = useContext(CasesContext);
  if (!ctx) throw new Error('useCases must be used within a CasesProvider');
  return ctx;
}
