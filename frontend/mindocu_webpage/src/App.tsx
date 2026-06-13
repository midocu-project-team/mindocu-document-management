import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './App.css'
import './components/workspace/workspace.css'
import { DocumentWorkspace } from './components/workspace/DocumentWorkspace'
// Simple landing kept inline to restore the original start screen
import MainLayout from './layouts/MainLayout'
import CaseHomePage from './pages/CaseHomePage'
import PdfUploadReview from './components/uploadpipeline/PdfUploadReview'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<MainLayout />}>
          <Route path="/" element={<CaseHomePage />} />
          <Route path="/pdf-review/:caseId" element={<PdfUploadReview />} />
        </Route>
        <Route path="/pdf-viewer/:caseId" element={<DocumentWorkspace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
