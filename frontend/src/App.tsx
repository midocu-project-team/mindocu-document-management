import { BrowserRouter, Routes, Route } from 'react-router-dom';
import './App.css';
import './components/workspace/workspace.css';
import { DocumentWorkspacePage } from './pages/DocumentWorkspacePage';
import MainLayout from './layouts/MainLayout';
import CaseHomePage from './pages/CaseHomePage';
import PdfUploadPage from './pages/PdfUploadPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<MainLayout />}>
          <Route path="/" element={<CaseHomePage />} />
          <Route path="/pdf-review/:caseId" element={<PdfUploadPage />} />
        </Route>
        <Route path="/pdf-viewer/:caseId" element={<DocumentWorkspacePage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
