import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
} from "react-router";

import Login from "./pages/auth/Login";
import Register from "./pages/auth/Register";

import AdminDashboard from "./pages/admin/AdminDashboard";
import ProfessorDashboard from "./pages/professor/ProfessorDashboard";
import StudentDashboard from "./pages/student/StudentDashboard";
import GuestDashboard from "./pages/guest/GuestDashboard";

import SystemStatus from "./pages/SystemStatus";
import NotFound from "./pages/NotFound";
import Unauthorized from "./pages/Unauthorized";

import ProtectedRoute from "./components/auth/ProtectedRoute";
import UserManagement from "./pages/admin/UserManagement";

function App() {
  return (
    <BrowserRouter>
      <Routes>

        {/* Public Routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* Administrator Routes */}
        <Route
          element={
            <ProtectedRoute allowedRoles={["Administrator"]} />
          }
        >
          <Route
            path="/admin/dashboard"
            element={<AdminDashboard />}
          />
        </Route>

        {/* Professor Routes */}
        <Route
          element={
            <ProtectedRoute allowedRoles={["Professor"]} />
          }
        >
          <Route
            path="/professor/dashboard"
            element={<ProfessorDashboard />}
          />
        </Route>

        {/* Student Routes */}
        <Route
          element={
            <ProtectedRoute allowedRoles={["Student"]} />
          }
        >
          <Route
            path="/student/dashboard"
            element={<StudentDashboard />}
          />
        </Route>

        {/* Guest Routes */}
        <Route
          element={
            <ProtectedRoute allowedRoles={["Guest"]} />
          }
        >
          <Route
            path="/guest/dashboard"
            element={<GuestDashboard />}
          />
        </Route>

        {/* Unauthorized */}
        <Route
          path="/unauthorized"
          element={<Unauthorized />}
        />

        {/* System Status */}
        <Route
          path="/system-status"
          element={<SystemStatus />}
        />

        {/* Default Route */}
        <Route
          path="/"
          element={<Navigate to="/login" replace />}
        />
        {/* Administrator Routes */}
        <Route
          element={
            <ProtectedRoute allowedRoles={["Administrator"]} />
          }
        >
          <Route
            path="/admin/dashboard"
            element={<AdminDashboard />}
          />

          <Route
            path="/admin/users"
            element={<UserManagement />}
          />
        </Route>

        {/* Not Found */}
        <Route path="*" element={<NotFound />} />

      </Routes>
    </BrowserRouter>
  );
}

export default App;
