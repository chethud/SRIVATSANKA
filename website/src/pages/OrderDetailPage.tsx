import { useCallback, useEffect, useState } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import type { Enquiry } from '../api/client';
import { EmptyState } from '../components/Layout';
import { OrderDetailView, type OrderPageView } from '../components/order/OrderDetailView';
import { useAppData } from '../context/AppDataContext';

export default function OrderDetailPage() {
  const { orderId } = useParams<{ orderId: string }>();
  const location = useLocation();
  const { enquiries, dishes, workers, patchEnquiry, refreshDishes, markEnquiryViewed } = useAppData();
  const onOrderUpdated = useCallback((updated: Enquiry) => {
    patchEnquiry(updated);
  }, [patchEnquiry]);
  const order = enquiries.find((e) => e.id === orderId && e.status === 'CONVERTED');

  const openCopy = (location.state as { openCopy?: OrderPageView } | null)?.openCopy;
  const [initialView] = useState<OrderPageView>(() =>
    openCopy === 'kitchen' || openCopy === 'billing' ? openCopy : 'details',
  );

  useEffect(() => {
    if (order && !order.ownerViewedAt) {
      void markEnquiryViewed(order.id);
    }
  }, [order, markEnquiryViewed]);

  if (!order) {
    return (
      <>
        <Link to="/orders" className="text-sm text-[var(--primary)] hover:underline inline-flex items-center gap-1 mb-4">
          <ArrowLeft size={16} /> Back to orders
        </Link>
        <EmptyState message="Order not found or not converted yet." />
      </>
    );
  }

  return (
    <OrderDetailView
      order={order}
      dishes={dishes}
      workers={workers}
      onOrderUpdated={onOrderUpdated}
      onDishesCatalogUpdated={refreshDishes}
      initialView={initialView}
    />
  );
}
