import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthLayout, AppLayout } from './components/layout'
import { ProtectedRoute } from './components/ProtectedRoute'
import { LoginPage, RegisterPage, DashboardPage, UploadPage, ResultsPage, GoalDetailPage, ComparePage } from './pages'

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
        <Route path="/compare" element={<ComparePage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
