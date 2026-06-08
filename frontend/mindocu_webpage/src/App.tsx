import './App.css'
import './components/workspace.css'
import { DocumentWorkspace } from './components/DocumentWorkspace'
// Simple landing kept inline to restore the original start screen

function App() {
  const path = typeof window !== 'undefined' ? window.location.pathname : '/'

  if (path.startsWith('/pdf-viewer')) {
    return <DocumentWorkspace />
  }

  return (
    <div style={{ padding: 48, fontFamily: 'Inter, system-ui, sans-serif' }}>
      <h1 style={{ margin: 0, fontSize: '2rem' }}>mindocu</h1>
      <p style={{ marginTop: 8 }}>Projektstart — öffne die PDF-Ansicht:</p>
      <p>
        <a href="/pdf-viewer">pdf-viewer</a>
      </p>
    </div>
  )
}

export default App
