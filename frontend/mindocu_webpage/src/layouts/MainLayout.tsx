import { Outlet } from 'react-router-dom';
import { Sidebar } from '../components/workspace/sidebar';

export default function MainLayout() {
  return (
    <div id="layout">
      <Sidebar />
      <main id="content">
        <Outlet />
      </main>
    </div>
  );
}
