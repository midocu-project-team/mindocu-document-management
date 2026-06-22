import { Outlet } from 'react-router-dom';
import { WorkspaceSidebar } from '../components/workspace/WorkspaceSidebar';

export default function MainLayout() {
  return (
    <div id="layout">
      <WorkspaceSidebar />
      <main id="content">
        <Outlet />
      </main>
    </div>
  );
}
