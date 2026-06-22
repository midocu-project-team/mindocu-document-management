import { Outlet } from 'react-router-dom';
import { AppSidebar } from '../components/common/AppSidebar';

export default function MainLayout() {
  return (
    <div id="layout">
      <AppSidebar />
      <main id="content">
        <Outlet />
      </main>
    </div>
  );
}
