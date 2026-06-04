import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, Download, Printer } from 'lucide-react';
import { Card, Button, EmptyState } from '../components/Layout';
import { OrderCopyView } from '../components/OrderCopyView';
import { useAppData } from '../context/AppDataContext';
import { downloadOrderCopy } from '../utils/orderCopies';

type Props = { copyType: 'kitchen' | 'billing' };

export default function OrderCopyPage({ copyType }: Props) {
  const { orderId } = useParams<{ orderId: string }>();
  const { enquiries } = useAppData();
  const order = enquiries.find((e) => e.id === orderId && e.status === 'CONVERTED');
  const title = copyType === 'kitchen' ? 'Kitchen Copy' : 'Billing Copy';

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
    <>
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6 print:hidden">
        <Link
          to={`/orders/${order.id}`}
          className="text-sm text-[var(--primary)] hover:underline inline-flex items-center gap-1"
        >
          <ArrowLeft size={16} /> Back to order
        </Link>
        <div className="flex gap-2">
          <Button type="button" onClick={() => window.print()} className="flex items-center gap-2">
            <Printer size={16} />
            Print
          </Button>
          <Button type="button" onClick={() => downloadOrderCopy(order, copyType)} className="flex items-center gap-2">
            <Download size={16} />
            Download
          </Button>
        </div>
      </div>

      <Card className="p-8 print:border-0 print:shadow-none">
        <OrderCopyView enquiry={order} copyType={copyType} />
      </Card>

      <p className="text-center text-sm text-[var(--muted)] mt-6 print:hidden">{title} for {order.customerName}</p>
    </>
  );
}
