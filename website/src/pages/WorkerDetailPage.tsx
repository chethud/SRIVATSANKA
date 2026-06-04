import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, Calendar, CheckCircle2, ClipboardList, IndianRupee, Phone, User, Wallet } from 'lucide-react';
import { PageHeader, Card, Button, EmptyState } from '../components/Layout';
import { useAppData } from '../context/AppDataContext';
import {
  createWorkerAssignment,
  deleteWorkerAssignment,
  fetchWorkerProfile,
  markWorkerAssignmentPaid,
  formatCurrency,
  formatDate,
  type WorkerProfile,
} from '../api/client';
import { formatOrderId } from '../utils/orderNotes';

const DUTY_TYPES = ['Kitchen', 'Service', 'Dispatch', 'Setup & breakdown', 'Supervision', 'Other'];

function defaultDutyDate() {
  return new Date().toISOString().slice(0, 10);
}

export default function WorkerDetailPage() {
  const { workerId } = useParams<{ workerId: string }>();
  const { enquiries, refresh } = useAppData();
  const [profile, setProfile] = useState<WorkerProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [showAssign, setShowAssign] = useState(false);
  const [assignForm, setAssignForm] = useState({
    dutyDate: defaultDutyDate(),
    enquiryId: '',
    dutyType: DUTY_TYPES[0],
    wage: '',
    notes: '',
  });
  const [saving, setSaving] = useState(false);
  const [payingId, setPayingId] = useState<string | null>(null);
  const [error, setError] = useState('');

  async function load() {
    if (!workerId) return;
    setLoading(true);
    setError('');
    try {
      setProfile(await fetchWorkerProfile(workerId));
    } catch {
      setError('Could not load worker profile.');
      setProfile(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [workerId]);

  async function handleAssign(e: React.FormEvent) {
    e.preventDefault();
    if (!workerId) return;
    setSaving(true);
    setError('');
    try {
      await createWorkerAssignment(workerId, {
        enquiryId: assignForm.enquiryId || null,
        dutyDate: new Date(`${assignForm.dutyDate}T09:00:00`).toISOString(),
        dutyType: assignForm.dutyType,
        wage: assignForm.wage === '' ? 0 : Number(assignForm.wage),
        notes: assignForm.notes || undefined,
      });
      setAssignForm({ dutyDate: defaultDutyDate(), enquiryId: '', dutyType: DUTY_TYPES[0], wage: '', notes: '' });
      setShowAssign(false);
      await load();
      refresh();
    } catch {
      setError('Could not save assignment.');
    } finally {
      setSaving(false);
    }
  }

  async function completePayment(assignmentId: string) {
    if (!workerId || !confirm('Make payment for this wage? It will be removed from open duties and wages due.')) return;
    setPayingId(assignmentId);
    setError('');
    try {
      await markWorkerAssignmentPaid(workerId, assignmentId);
      await load();
      refresh();
    } catch {
      setError('Could not mark payment as completed.');
    } finally {
      setPayingId(null);
    }
  }

  async function removeAssignment(assignmentId: string) {
    if (!workerId || !confirm('Remove this duty from history?')) return;
    await deleteWorkerAssignment(workerId, assignmentId);
    await load();
    refresh();
  }

  if (loading) {
    return <p className="text-sm text-[var(--muted)] py-12 text-center">Loading worker profile…</p>;
  }

  if (!profile) {
    return (
      <>
        <Link to="/workers" className="text-sm text-[var(--primary)] hover:underline inline-flex items-center gap-1 mb-4">
          <ArrowLeft size={16} /> Back to workers
        </Link>
        <EmptyState message="Worker not found." />
      </>
    );
  }

  const { worker } = profile;
  const orders = enquiries.length > 0 ? enquiries : [];

  return (
    <>
      <Link to="/workers" className="text-sm text-[var(--muted)] hover:text-[var(--primary)] inline-flex items-center gap-2 mb-4">
        <ArrowLeft size={18} /> Back to workers
      </Link>

      <PageHeader
        title={worker.name}
        description={`${worker.role} · ${worker.phoneNumber}`}
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {[
          { icon: User, label: 'Role', value: worker.role },
          { icon: Phone, label: 'Phone', value: worker.phoneNumber },
          { icon: ClipboardList, label: 'Open duties', value: String(profile.totalDuties) },
          { icon: IndianRupee, label: 'Wages due', value: formatCurrency(profile.totalWagesEarned) },
        ].map(({ icon: Icon, label, value }) => (
          <Card key={label} className="p-4">
            <Icon size={18} className="text-[var(--order-accent)] mb-2" />
            <p className="text-[10px] uppercase tracking-wide text-[var(--order-accent)]">{label}</p>
            <p className="text-sm font-semibold mt-1">{value}</p>
          </Card>
        ))}
      </div>

      {error && <p className="text-sm text-[var(--danger)] mb-4">{error}</p>}

      <Card className="p-6 mb-6">
        <Button type="button" className="mb-4" onClick={() => setShowAssign((v) => !v)}>
          {showAssign ? 'Cancel' : 'Assign duty to order'}
        </Button>

        {showAssign && (
          <form onSubmit={handleAssign} className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 rounded-xl border border-[var(--border)] bg-[var(--background)]">
            <div>
              <label className="text-xs text-[var(--muted)] flex items-center gap-1 mb-1">
                <Calendar size={12} /> Duty date
              </label>
              <input
                type="date"
                required
                value={assignForm.dutyDate}
                onChange={(e) => setAssignForm({ ...assignForm, dutyDate: e.target.value })}
                className="form-input w-full px-3 py-2 rounded-lg text-sm"
              />
            </div>
            <div>
              <label className="text-xs text-[var(--muted)] mb-1 block">Order</label>
              <select
                required
                value={assignForm.enquiryId}
                onChange={(e) => setAssignForm({ ...assignForm, enquiryId: e.target.value })}
                className="form-select w-full px-3 py-2 rounded-lg text-sm"
              >
                <option value="">Select order…</option>
                {orders.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.status === 'CONVERTED' ? '[Order] ' : ''}
                    {o.customerName} — {o.eventType} ({formatDate(o.eventDate)})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-[var(--muted)] mb-1 block">Duty type</label>
              <select
                value={assignForm.dutyType}
                onChange={(e) => setAssignForm({ ...assignForm, dutyType: e.target.value })}
                className="form-select w-full px-3 py-2 rounded-lg text-sm"
              >
                {DUTY_TYPES.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-[var(--muted)] flex items-center gap-1 mb-1">
                <IndianRupee size={12} /> Wage for this order (₹)
              </label>
              <input
                type="number"
                min={0}
                required
                placeholder="e.g. 1200"
                value={assignForm.wage}
                onChange={(e) => setAssignForm({ ...assignForm, wage: e.target.value })}
                className="form-input w-full px-3 py-2 rounded-lg text-sm"
              />
            </div>
            <input
              placeholder="Notes (optional)"
              value={assignForm.notes}
              onChange={(e) => setAssignForm({ ...assignForm, notes: e.target.value })}
              className="form-input md:col-span-2 px-3 py-2 rounded-lg text-sm"
            />
            <div className="md:col-span-2">
              <Button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save assignment'}</Button>
            </div>
          </form>
        )}
      </Card>

      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <ClipboardList size={20} /> Work history
        </h3>
        {profile.assignments.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">No assignments yet. Add a duty linked to an order with wage above.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm data-table">
              <thead>
                <tr>
                  <th className="text-left p-3">Date</th>
                  <th className="text-left p-3">Order</th>
                  <th className="text-left p-3">Duty</th>
                  <th className="text-left p-3">Wage</th>
                  <th className="text-left p-3">Payment</th>
                  <th className="text-left p-3" />
                </tr>
              </thead>
              <tbody>
                {profile.assignments.map((a) => (
                  <tr
                    key={a.id}
                    className={`border-t border-[var(--border)] ${a.paymentCompleted ? 'opacity-60' : ''}`}
                  >
                    <td className="p-3">{formatDate(a.dutyDate)}</td>
                    <td className="p-3">
                      {a.orderLabel ? (
                        <>
                          <span className="font-medium">{a.orderLabel}</span>
                          {a.enquiryId && (
                            <Link to={`/orders/${a.enquiryId}`} className="block text-xs text-[var(--primary)] mt-1">
                              {formatOrderId(a.enquiryId)} →
                            </Link>
                          )}
                        </>
                      ) : (
                        <span className="text-[var(--muted)]">—</span>
                      )}
                    </td>
                    <td className="p-3">{a.dutyType}</td>
                    <td className="p-3 font-medium tabular-nums">{formatCurrency(a.wage)}</td>
                    <td className="p-3">
                      {a.paymentCompleted ? (
                        <span className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1.5 rounded-lg bg-[var(--primary-light)] text-[var(--primary)]">
                          <CheckCircle2 size={14} /> Payment completed
                        </span>
                      ) : (
                        <button
                          type="button"
                          disabled={payingId === a.id}
                          onClick={() => completePayment(a.id)}
                          className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1.5 rounded-lg border border-[var(--primary)] text-[var(--primary)] hover:bg-[var(--primary)] hover:text-white transition-colors disabled:opacity-50"
                        >
                          <Wallet size={14} />
                          {payingId === a.id ? 'Processing…' : 'Make payment'}
                        </button>
                      )}
                    </td>
                    <td className="p-3">
                      <button
                        type="button"
                        onClick={() => removeAssignment(a.id)}
                        className="text-xs text-red-600 hover:underline"
                      >
                        Remove
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  );
}
