import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Calendar, ClipboardList, Phone, Trash2, User, X } from 'lucide-react';
import { Button, Card } from '../Layout';
import type { Enquiry, Worker } from '../../api/client';
import {
  createWorkerAssignment,
  deleteWorkerAssignment,
  fetchWorkerProfile,
  formatDate,
  type WorkerProfile,
} from '../../api/client';
import { formatOrderId } from '../../utils/orderNotes';

const DUTY_TYPES = [
  'Kitchen',
  'Service',
  'Dispatch',
  'Setup & breakdown',
  'Supervision',
  'Other',
];

function defaultDutyDate() {
  return new Date().toISOString().slice(0, 10);
}

export function WorkerProfilePanel({
  worker,
  orders,
  onClose,
  onUpdated,
}: {
  worker: Worker;
  orders: Enquiry[];
  onClose: () => void;
  onUpdated: () => void;
}) {
  const [profile, setProfile] = useState<WorkerProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [showAssign, setShowAssign] = useState(false);
  const [assignForm, setAssignForm] = useState({
    dutyDate: defaultDutyDate(),
    enquiryId: '',
    dutyType: DUTY_TYPES[0],
    notes: '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  async function load() {
    setLoading(true);
    setError('');
    try {
      const p = await fetchWorkerProfile(worker.id);
      setProfile(p);
    } catch {
      setError('Could not load worker history.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [worker.id]);

  async function handleAssign(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      await createWorkerAssignment(worker.id, {
        enquiryId: assignForm.enquiryId || null,
        dutyDate: new Date(`${assignForm.dutyDate}T09:00:00`).toISOString(),
        dutyType: assignForm.dutyType,
        notes: assignForm.notes || undefined,
      });
      setAssignForm({ dutyDate: defaultDutyDate(), enquiryId: '', dutyType: DUTY_TYPES[0], notes: '' });
      setShowAssign(false);
      await load();
      onUpdated();
    } catch {
      setError('Could not save duty assignment.');
    } finally {
      setSaving(false);
    }
  }

  async function removeAssignment(assignmentId: string) {
    if (!confirm('Remove this duty from history?')) return;
    await deleteWorkerAssignment(worker.id, assignmentId);
    await load();
    onUpdated();
  }

  const orderOptions = orders.filter((e) => e.status === 'CONVERTED');
  const allOrders = orders.length > 0 ? orders : orderOptions;

  return (
    <Card className="p-6 h-fit sticky top-4">
      <div className="flex items-start justify-between gap-2 mb-4">
        <div>
          <h3 className="text-lg font-semibold text-[var(--foreground)] flex items-center gap-2">
            <User size={20} className="text-[var(--primary)]" />
            {worker.name}
            {(worker.isLead ?? false) && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--primary-light)] text-[var(--primary)]">
                ★ Lead
              </span>
            )}
          </h3>
          <p className="text-sm text-[var(--muted)]">{worker.role}</p>
        </div>
        <button type="button" onClick={onClose} className="p-2 rounded-lg hover:bg-[var(--sidebar-hover)]" aria-label="Close">
          <X size={18} />
        </button>
      </div>

      <dl className="grid grid-cols-2 gap-3 text-sm mb-5 pb-5 border-b border-[var(--border)]">
        <div>
          <dt className="text-[var(--muted)] text-xs flex items-center gap-1"><Phone size={12} /> Phone</dt>
          <dd className="font-medium">{worker.phoneNumber}</dd>
        </div>
        <div>
          <dt className="text-[var(--muted)] text-xs">Daily wage</dt>
          <dd className="font-medium">₹{worker.dailyWage}</dd>
        </div>
        {profile && (
          <>
            <div>
              <dt className="text-[var(--muted)] text-xs">Total duties</dt>
              <dd className="font-medium">{profile.totalDuties}</dd>
            </div>
            <div>
              <dt className="text-[var(--muted)] text-xs">Upcoming</dt>
              <dd className="font-medium">{profile.upcomingDuties}</dd>
            </div>
          </>
        )}
      </dl>

      {error && <p className="text-sm text-[var(--danger)] mb-3">{error}</p>}

      <Button
        type="button"
        className="w-full mb-4 !py-2.5"
        onClick={() => setShowAssign((v) => !v)}
      >
        {showAssign ? 'Cancel assign' : 'Assign duty (date & order)'}
      </Button>

      {showAssign && (
        <form onSubmit={handleAssign} className="mb-6 p-4 rounded-xl border border-[var(--border)] bg-[var(--background)] space-y-3">
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
            <label className="text-xs text-[var(--muted)] mb-1 block">Order (optional)</label>
            <select
              value={assignForm.enquiryId}
              onChange={(e) => setAssignForm({ ...assignForm, enquiryId: e.target.value })}
              className="form-select w-full px-3 py-2 rounded-lg text-sm"
            >
              <option value="">General duty — no specific order</option>
              {allOrders.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.status === 'CONVERTED' ? '★ ' : ''}
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
          <input
            placeholder="Notes (optional)"
            value={assignForm.notes}
            onChange={(e) => setAssignForm({ ...assignForm, notes: e.target.value })}
            className="form-input w-full px-3 py-2 rounded-lg text-sm"
          />
          <Button type="submit" disabled={saving} className="w-full">
            {saving ? 'Saving…' : 'Save assignment'}
          </Button>
        </form>
      )}

      <h4 className="text-sm font-semibold text-[var(--foreground)] flex items-center gap-2 mb-3">
        <ClipboardList size={16} /> Work history
      </h4>

      {loading ? (
        <p className="text-sm text-[var(--muted)]">Loading history…</p>
      ) : !profile?.assignments.length ? (
        <p className="text-sm text-[var(--muted)]">No duties assigned yet. Use Assign duty above.</p>
      ) : (
        <ul className="space-y-3 max-h-[420px] overflow-y-auto pr-1">
          {profile.assignments.map((a) => (
            <li
              key={a.id}
              className="p-3 rounded-xl border border-[var(--border)] bg-[var(--background)] text-sm"
            >
              <div className="flex justify-between gap-2 items-start">
                <div>
                  <p className="font-medium text-[var(--foreground)]">{a.dutyType}</p>
                  <p className="text-xs text-[var(--muted)] mt-0.5">{formatDate(a.dutyDate)}</p>
                </div>
                <button
                  type="button"
                  onClick={() => removeAssignment(a.id)}
                  className="p-1.5 text-[var(--muted)] hover:text-red-600 shrink-0"
                  title="Remove"
                >
                  <Trash2 size={14} />
                </button>
              </div>
              {a.orderLabel ? (
                <p className="mt-2 text-[var(--foreground)]">
                  {a.orderLabel}
                  {a.eventLocation && (
                    <span className="text-[var(--muted)]"> · {a.eventLocation}</span>
                  )}
                </p>
              ) : (
                <p className="mt-2 text-[var(--muted)]">General duty</p>
              )}
              {a.enquiryId && (
                <Link
                  to={`/orders/${a.enquiryId}`}
                  className="inline-block mt-2 text-xs text-[var(--primary)] hover:underline"
                >
                  Open order {formatOrderId(a.enquiryId)} →
                </Link>
              )}
              {a.notes && <p className="mt-1 text-xs text-[var(--muted)]">{a.notes}</p>}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
