import { Routes, Route, Navigate } from 'react-router-dom'
import { AppLayout } from './components/layout'
import { ProtectedRoute, RequireUploader } from './components/ProtectedRoute'
import { LandingPage, CouncilPage, BrowsePage, PublicComparePage, AccessPage, LimitationsPage, HowItWorksPage, DashboardPage, UploadPage, ResultsPage, GoalDetailPage, ActivitiesPage, GapsPage, ExportPage, AdminPage } from './pages'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/council/:code" element={<CouncilPage />} />
      <Route path="/councils" element={<BrowsePage />} />
      <Route path="/compare" element={<PublicComparePage />} />
      <Route path="/access" element={<AccessPage />} />
      <Route path="/limitations" element={<LimitationsPage />} />
      <Route path="/how-it-works" element={<HowItWorksPage />} />
      <Route path="/login" element={<Navigate to="/access" replace />} />
      <Route path="/register" element={<Navigate to="/access" replace />} />
      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<RequireUploader><DashboardPage /></RequireUploader>} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/results/:id" element={<ResultsPage />} />
        <Route path="/results/:id/goal/:sdg" element={<GoalDetailPage />} />
        <Route path="/results/:id/activities" element={<ActivitiesPage />} />
        <Route path="/results/:id/gaps" element={<GapsPage />} />
        <Route path="/results/:id/export" element={<ExportPage />} />
        <Route path="/admin" element={<AdminPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
