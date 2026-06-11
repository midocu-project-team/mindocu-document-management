import { WorkspaceSidebar } from './WorkspaceSidebar'

// Backwards-compatible alias: `Sidebar` previously existed as the main
// left navigation component. Export a `Sidebar` component that renders the
// existing `WorkspaceSidebar` so older imports or expectations keep working.
export function Sidebar() {
  return <WorkspaceSidebar />
}

export default Sidebar
