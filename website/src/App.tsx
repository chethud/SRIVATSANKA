import { Routes, Route, Navigate } from 'react-router-dom';
import { DashboardLayout } from './components/Layout';
import { GuestOnly } from './components/GuestOnly';
import { RequireAuth } from './components/RequireAuth';
import LoginPage from './pages/LoginPage';
import ResetPasswordPage from './pages/ResetPasswordPage';
import DashboardPage from './pages/DashboardPage';
import EnquiriesPage from './pages/EnquiriesPage';
import OrdersPage from './pages/OrdersPage';
import OrderDetailPage from './pages/OrderDetailPage';
import OrderCopyPage from './pages/OrderCopyPage';
import DishesPage from './pages/DishesPage';
import VendorsPage from './pages/VendorsPage';
import WorkersPage from './pages/WorkersPage';
import WorkerDetailPage from './pages/WorkerDetailPage';
import InvoicesPage from './pages/InvoicesPage';
import AnalyticsPage from './pages/AnalyticsPage';
import SettingsPage from './pages/SettingsPage';
import BotTesterPage from './pages/BotTesterPage';
import PhotosPage from './pages/PhotosPage';

export default function App() {
  return (
    <Routes>
      <Route element={<GuestOnly />}>
        <Route path="/login" element={<LoginPage />} />
      </Route>
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route element={<RequireAuth />}>
      <Route element={<DashboardLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="enquiries" element={<EnquiriesPage />} />
        <Route path="orders" element={<OrdersPage />} />
        <Route path="orders/:orderId" element={<OrderDetailPage />} />
        <Route path="orders/:orderId/kitchen" element={<OrderCopyPage copyType="kitchen" />} />
        <Route path="orders/:orderId/billing" element={<OrderCopyPage copyType="billing" />} />
        <Route path="dishes" element={<DishesPage />} />
        <Route path="vendors" element={<VendorsPage />} />
        <Route path="workers" element={<WorkersPage />} />
        <Route path="workers/:workerId" element={<WorkerDetailPage />} />
        <Route path="invoices" element={<InvoicesPage />} />
        <Route path="invoices/:uploadId" element={<InvoicesPage />} />
        <Route path="expenses" element={<Navigate to="/invoices" replace />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route path="bot-tester" element={<BotTesterPage />} />
        <Route path="photos" element={<PhotosPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
      </Route>
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
