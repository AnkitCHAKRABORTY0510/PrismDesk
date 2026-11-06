import { BrowserRouter, Navigate, Route, Routes } from "react-router";

import ProtectedRoute from "./components/auth/ProtectedRoute";
import AppLayout from "./components/layout/AppLayout";
import { useAuth } from "./context/AuthContext";
import NotFound from "./pages/NotFound";
import SystemStatus from "./pages/SystemStatus";
import Unauthorized from "./pages/Unauthorized";
import Announcements from "./pages/admin/Announcements";
import AuditLogs from "./pages/admin/AuditLogs";
import SystemSettings from "./pages/admin/SystemSettings";
import UserManagement from "./pages/admin/UserManagement";
import Login from "./pages/auth/Login";
import Register from "./pages/auth/Register";
import ConferenceList from "./pages/conferences/ConferenceList";
import Dashboard from "./pages/dashboard/Dashboard";
import EntryDetail from "./pages/handbook/EntryDetail";
import Handbook from "./pages/handbook/Handbook";
import ProjectDetail from "./pages/projects/ProjectDetail";
import ProjectList from "./pages/projects/ProjectList";
import PaperDetail from "./pages/research/PaperDetail";
import ResearchLibrary from "./pages/research/ResearchLibrary";
import NotificationSettings from "./pages/settings/NotificationSettings";
import TaskDetail from "./pages/tasks/TaskDetail";
import TaskList from "./pages/tasks/TaskList";

function HomeRedirect() {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return null;
  return <Navigate to={isAuthenticated ? "/dashboard" : "/login"} replace />;
}

export function AppRoutes() {
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/unauthorized" element={<Unauthorized />} />
      <Route path="/system-status" element={<SystemStatus />} />
      <Route path="/" element={<HomeRedirect />} />

      {/* Authenticated application shell */}
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/dashboard" element={<Dashboard />} />

          {/* Legacy role dashboard URLs */}
          <Route path="/admin/dashboard" element={<Navigate to="/dashboard" replace />} />
          <Route path="/professor/dashboard" element={<Navigate to="/dashboard" replace />} />
          <Route path="/student/dashboard" element={<Navigate to="/dashboard" replace />} />
          <Route path="/guest/dashboard" element={<Navigate to="/dashboard" replace />} />

          <Route element={<ProtectedRoute capability="projects.view" />}>
            <Route path="/projects" element={<ProjectList />} />
            <Route path="/projects/:projectId" element={<ProjectDetail />} />
          </Route>

          <Route element={<ProtectedRoute capability="research.view" />}>
            <Route path="/research" element={<ResearchLibrary />} />
          </Route>
          {/* Guests may open papers linked to projects they can read. */}
          <Route path="/research/papers/:paperId" element={<PaperDetail />} />

          <Route element={<ProtectedRoute capability="tasks.view" />}>
            <Route path="/tasks" element={<TaskList />} />
            <Route path="/tasks/:taskId" element={<TaskDetail />} />
          </Route>

          <Route element={<ProtectedRoute capability="handbook.view" />}>
            <Route path="/handbook" element={<Handbook />} />
            <Route path="/handbook/entries/:entryId" element={<EntryDetail />} />
          </Route>

          <Route path="/conferences" element={<ConferenceList />} />
          <Route path="/settings/notifications" element={<NotificationSettings />} />

          <Route element={<ProtectedRoute capability="users.manage" />}>
            <Route path="/admin/users" element={<UserManagement />} />
          </Route>
          <Route element={<ProtectedRoute capability="audit.view" />}>
            <Route path="/admin/audit" element={<AuditLogs />} />
          </Route>
          <Route element={<ProtectedRoute capability="announcements.send" />}>
            <Route path="/admin/announcements" element={<Announcements />} />
          </Route>
          <Route element={<ProtectedRoute capability="settings.view" />}>
            <Route path="/admin/settings" element={<SystemSettings />} />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
}

export default App;
