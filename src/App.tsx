import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/auth/LoginPage';
import { RegisterPage } from './pages/auth/RegisterPage';
import { UserDashboard } from './pages/user/UserDashboard';
import { AssetsPage } from './pages/user/AssetsPage';
import { ViolationsPage } from './pages/user/ViolationsPage';
import { AdminDashboard } from './pages/admin/AdminDashboard';
import { BlockchainProofCenter } from './pages/user/BlockchainProofCenter';
import { DMCACenter } from './pages/user/DMCACenter';
import { ForecastPage } from './pages/user/ForecastPage';
import { ThreatMap } from './pages/user/ThreatMap';
import { ProfilePage } from './pages/user/ProfilePage';
import { SettingsPage } from './pages/shared/SettingsPage';
import { HelpSupportPage } from './pages/shared/HelpSupportPage';
import { WorkInProgress } from './components/shared/WorkInProgress';
import { motion, AnimatePresence } from 'motion/react';
import { PageTransition } from './components/shared/PageTransition';
import { AuthProvider } from './context/AuthContext';
import { RequireAdmin, RequireAuth } from './components/shared/ProtectedRoute';

import { GlobalToast } from './components/shared/GlobalToast';

function AnimatedRoutes() {
  const location = useLocation();
  
  return (
    <AnimatePresence mode="wait">
      <div key={location.pathname} className="w-full h-full">
        <Routes location={location}>
          <Route path="/" element={<PageTransition><LandingPage /></PageTransition>} />
        <Route path="/login" element={<PageTransition><LoginPage /></PageTransition>} />
        <Route path="/register" element={<PageTransition><RegisterPage /></PageTransition>} />
        
        {/* User Routes */}
        <Route path="/dashboard" element={<RequireAuth><PageTransition><UserDashboard /></PageTransition></RequireAuth>} />
        <Route path="/assets" element={<RequireAuth><PageTransition><AssetsPage /></PageTransition></RequireAuth>} />
        <Route path="/violations" element={<RequireAuth><PageTransition><ViolationsPage /></PageTransition></RequireAuth>} />
        <Route path="/threat-map" element={<RequireAuth><PageTransition><ThreatMap /></PageTransition></RequireAuth>} />
        <Route path="/blockchain" element={<RequireAuth><PageTransition><BlockchainProofCenter /></PageTransition></RequireAuth>} />
        <Route path="/dmca" element={<RequireAuth><PageTransition><DMCACenter /></PageTransition></RequireAuth>} />
        <Route path="/forecast" element={<RequireAuth><PageTransition><ForecastPage /></PageTransition></RequireAuth>} />
        <Route path="/profile" element={<RequireAuth><PageTransition><ProfilePage /></PageTransition></RequireAuth>} />
        <Route path="/settings" element={<RequireAuth><PageTransition><SettingsPage /></PageTransition></RequireAuth>} />
        <Route path="/help" element={<RequireAuth><PageTransition><HelpSupportPage /></PageTransition></RequireAuth>} />
        
        {/* Admin Routes */}
        <Route path="/admin" element={<RequireAdmin><PageTransition><AdminDashboard /></PageTransition></RequireAdmin>} />
        <Route path="/admin/violations" element={<RequireAdmin><PageTransition><WorkInProgress title="All Violations" /></PageTransition></RequireAdmin>} />
        <Route path="/admin/crawl-feed" element={<RequireAdmin><PageTransition><WorkInProgress title="Live Crawl Feed" /></PageTransition></RequireAdmin>} />
        <Route path="/admin/threat-map" element={<RequireAdmin><PageTransition><WorkInProgress title="Threat Map" /></PageTransition></RequireAdmin>} />
        <Route path="/admin/organizations" element={<RequireAdmin><PageTransition><WorkInProgress title="Organizations" /></PageTransition></RequireAdmin>} />
        <Route path="/admin/assets" element={<RequireAdmin><PageTransition><WorkInProgress title="All Assets" /></PageTransition></RequireAdmin>} />
        <Route path="/admin/blockchain" element={<RequireAdmin><PageTransition><WorkInProgress title="Blockchain Registry" /></PageTransition></RequireAdmin>} />
        <Route path="/admin/ai-health" element={<RequireAdmin><PageTransition><WorkInProgress title="AI Service Health" /></PageTransition></RequireAdmin>} />
        <Route path="/admin/crawlers" element={<RequireAdmin><PageTransition><WorkInProgress title="Crawler Status" /></PageTransition></RequireAdmin>} />
        <Route path="/admin/logs" element={<RequireAdmin><PageTransition><WorkInProgress title="System Logs" /></PageTransition></RequireAdmin>} />
        <Route path="/admin/settings" element={<RequireAdmin><PageTransition><WorkInProgress title="Platform Settings" /></PageTransition></RequireAdmin>} />
        <Route path="/admin/users" element={<RequireAdmin><PageTransition><WorkInProgress title="Admin Users" /></PageTransition></RequireAdmin>} />
        <Route path="/admin/*" element={<RequireAdmin><PageTransition><AdminDashboard /></PageTransition></RequireAdmin>} />
        
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  </AnimatePresence>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <GlobalToast />
        <AnimatedRoutes />
      </BrowserRouter>
    </AuthProvider>
  );
}
