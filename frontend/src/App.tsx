import { useEffect } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { api } from '@/lib/api';
import AnalyticsPage from '@/pages/Analytics';
import ForecastExplorerPage from '@/pages/ForecastExplorer';
import InventoryPage from '@/pages/Inventory';
import LoginPage from '@/pages/Login';
import MonitorPage from '@/pages/Monitor';
import MorningBriefPage from '@/pages/MorningBrief';
import { useAuthStore } from '@/store/auth';

export default function App() {
  const { token, user, setUser } = useAuthStore();

  useEffect(() => {
    if (token && !user) {
      api.me().then(setUser).catch(() => useAuthStore.getState().logout());
    }
  }, [token, user, setUser]);

  if (!token) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  return (
    <Routes>
      <Route path="/login" element={<Navigate to="/" replace />} />
      <Route element={<Layout />}>
        <Route index element={<MorningBriefPage />} />
        <Route path="forecast" element={<ForecastExplorerPage />} />
        <Route path="inventory" element={<InventoryPage />} />
        <Route path="monitor" element={<MonitorPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
