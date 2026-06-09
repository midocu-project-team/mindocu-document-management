import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './App.css'
import './components/workspace.css'
import { DocumentWorkspace } from './components/DocumentWorkspace'
// Simple landing kept inline to restore the original start screen
import MainLayout from './layouts/MainLayout'
import CaseHomePage from './pages/CaseHomePage'

function App() {
  const path = typeof window !== 'undefined' ? window.location.pathname : '/'

  if (path.startsWith('/pdf-viewer')) {
    return <DocumentWorkspace />
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route element={<MainLayout />}>
          <Route path="/" element={<CaseHomePage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
