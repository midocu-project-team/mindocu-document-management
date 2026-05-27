import './App.css'
import { Sidebar } from './components/sidebar'

function App() {
  return (
    <div id="layout">
      <Sidebar />
      <section id="content">
        <h1>Center</h1>
      </section>
    </div>
  )
}

export default App
