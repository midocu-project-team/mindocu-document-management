import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './App.css'
import MainLayout from './layouts/MainLayout'
import CaseHomePage from './pages/CaseHomePage'
import PdfUploadReview from './components/uploadpipeline/PdfUploadReview'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<MainLayout />}>
          <Route path="/" element={<CaseHomePage />} />
          <Route path="/pdf-review" element={<PdfUploadReview />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
