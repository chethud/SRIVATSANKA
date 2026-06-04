import { Routes, Route } from 'react-router-dom';
import { DashboardLayout } from './components/Layout';
import DashboardPage from './pages/DashboardPage';
import EnquiriesPage from './pages/EnquiriesPage';
import OrdersPage from './pages/OrdersPage';
import OrderDetailPage from './pages/OrderDetailPage';
import OrderCopyPage from './pages/OrderCopyPage';
import DishesPage from './pages/DishesPage';
import VendorsPage from './pages/VendorsPage';
import WorkersPage from './pages/WorkersPage';
import InvoicesPage from './pages/InvoicesPage';
import AnalyticsPage from './pages/AnalyticsPage';
import AIAssistantPage from './pages/AIAssistantPage';
import SettingsPage from './pages/SettingsPage';
import BotTesterPage from './pages/BotTesterPage';

export default function App() {
  return (
    <Routes>
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
        <Route path="invoices" element={<InvoicesPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route path="ai-assistant" element={<AIAssistantPage />} />
        <Route path="bot-tester" element={<BotTesterPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}
