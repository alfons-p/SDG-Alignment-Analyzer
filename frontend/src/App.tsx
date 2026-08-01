import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthLayout, AppLayout } from './components/layout'
import { ProtectedRoute } from './components/ProtectedRoute'
import { LoginPage, RegisterPage, DashboardPage, UploadPage, ResultsPage, GoalDetailPage, ActivitiesPage, GapsPage, ComparePage, AdminPage } from './pages'

export default function App() {
  return (
    <Routes>
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
      </Route>
      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<DashboardPage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/results/:id" element={<ResultsPage />} />
        <Route path="/results/:id/goal/:sdg" element={<GoalDetailPage />} />
        <Route path="/results/:id/activities" element={<ActivitiesPage />} />
        <Route path="/results/:id/gaps" element={<GapsPage />} />
        <Route path="/compare" element={<ComparePage />} />
        <Route path="/admin" element={<AdminPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
