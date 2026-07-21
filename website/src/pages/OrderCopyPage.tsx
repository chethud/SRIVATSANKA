import { useEffect } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { EmptyState } from '../components/Layout';
import { useAppData } from '../context/AppDataContext';

type Props = { copyType: 'kitchen' | 'billing' };

/** Legacy routes — send users back to the order page (copies open in-place there). */
export default function OrderCopyPage({ copyType }: Props) {
  const { orderId } = useParams<{ orderId: string }>();
  const { enquiries } = useAppData();
  const navigate = useNavigate();
  const order = enquiries.find((e) => e.id === orderId && e.status === 'CONVERTED');

  useEffect(() => {
    if (order) {
      navigate(`/orders/${order.id}`, { replace: true, state: { openCopy: copyType } });
    }
  }, [order, copyType, navigate]);

  if (!order) {
    return (
      <>
        <Link to="/orders" className="text-sm text-[var(--primary)] hover:underline inline-flex items-center gap-1 mb-4">
          <ArrowLeft size={16} /> Back to orders
        </Link>
        <EmptyState message="Order not found." />
      </>
    );
  }

  return (
    <p className="text-sm text-[var(--muted)]">Opening {copyType === 'kitchen' ? 'kitchen' : 'order'} copy…</p>
  );
}
