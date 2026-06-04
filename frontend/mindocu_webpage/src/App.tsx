import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './App.css'
import MainLayout from './layouts/MainLayout'
import CaseHomePage from './pages/CaseHomePage'

function App() {
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
