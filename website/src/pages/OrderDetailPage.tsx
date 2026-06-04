import { Link, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { EmptyState } from '../components/Layout';
import { OrderDetailView } from '../components/order/OrderDetailView';
import { useAppData } from '../context/AppDataContext';

export default function OrderDetailPage() {
  const { orderId } = useParams<{ orderId: string }>();
  const { enquiries, dishes, refresh } = useAppData();
  const order = enquiries.find((e) => e.id === orderId && e.status === 'CONVERTED');

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

  return <OrderDetailView order={order} dishes={dishes} onRefresh={refresh} />;
}
