import { useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { CheckCircle2, FileText, Upload, XCircle } from 'lucide-react';
import { PageHeader, Card, Button } from '../components/Layout';
import { ExpenseBillsPanel } from '../components/ExpenseBillsPanel';
import { PartialPaymentsPanel } from '../components/PartialPaymentsPanel';
import { useAppData } from '../context/AppDataContext';
import { useCreateActionListener } from '../hooks/useCreateActionListener';
import {
  cancelPendingInvoice,
  confirmExpenseInvoice,
  formatCurrency,
  recognizeExpenseInvoice,
  type InvoiceRecognizePreview,
} from '../api/client';
import { isPartialPaymentOrder } from '../utils/orderBilling';

type ReviewForm = {
  description: string;
  expenseDate: string;
  amount: string;
  purpose: string;
};

function previewToForm(p: InvoiceRecognizePreview): ReviewForm {
  return {
    description: p.description ?? '',
    expenseDate: p.expenseDate ?? '',
    amount: p.amount != null ? String(p.amount) : '',
    purpose: p.purpose ?? '',
  };
}

export default function InvoicesPage() {
  const { refresh, enquiries, patchEnquiry, analytics } = useAppData();
  const { uploadId } = useParams<{ uploadId?: string }>();
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [recognizing, setRecognizing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [preview, setPreview] = useState<InvoiceRecognizePreview | null>(null);
  const [form, setForm] = useState<ReviewForm>({ description: '', expenseDate: '', amount: '', purpose: '' });
  const [needsEdit, setNeedsEdit] = useState(false);
  const [savedMsg, setSavedMsg] = useState('');
  const [error, setError] = useState('');
  const partialCount = enquiries.filter(isPartialPaymentOrder).length;
  const expenseItems = analytics?.expense_items ?? [];

  useCreateActionListener('invoice', () => {
    fileInputRef.current?.click();
  });

  function resetFlow() {
    if (preview?.pendingId) {
      cancelPendingInvoice(preview.pendingId).catch(() => undefined);
    }
    setPreview(null);
    setForm({ description: '', expenseDate: '', amount: '', purpose: '' });
    setNeedsEdit(false);
    setError('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  }

  async function handleFileSelect(file: File) {
    if (preview?.pendingId) {
      await cancelPendingInvoice(preview.pendingId).catch(() => undefined);
    }
    setRecognizing(true);
    setError('');
    setSavedMsg('');
    setPreview(null);
    setNeedsEdit(false);
    try {
      const result = await recognizeExpenseInvoice(file);
      setPreview(result);
      setForm(previewToForm(result));
    } catch {
      setError('Could not read the invoice. Check the API connection and try again.');
      setPreview(null);
    } finally {
      setRecognizing(false);
    }
  }

  async function saveInvoice() {
    if (!preview) return;
    setSaving(true);
    setError('');
    try {
      const saved = await confirmExpenseInvoice({
        pendingId: preview.pendingId,
        description: form.description || undefined,
        expenseDate: form.expenseDate || undefined,
        amount: form.amount === '' ? undefined : Number(form.amount),
        purpose: form.purpose || undefined,
      });
      setSavedMsg('Invoice saved. It is now included in Analytics.');
      setPreview(null);
      setNeedsEdit(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
      await refresh();
      if (saved?.id) navigate(`/invoices/${saved.id}`, { replace: true });
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Could not save.';
      setError(msg.includes('expired') || msg.includes('404') ? `${msg} Upload the bill again.` : msg);
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Expenses Invoice"
        description="Upload expense bills, review saved expenses, and clear split-payment balances still due from customers."
      />

      <input
        ref={fileInputRef}
        type="file"
        accept=".jpg,.jpeg,.png,.webp,.pdf"
        className="hidden"
        disabled={recognizing || saving}
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) handleFileSelect(f);
        }}
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8 items-start">
        <div className="flex flex-col min-w-0">
          {!preview ? (
            <Card className="p-4 sm:p-6 lg:p-8">
              <h3 className="text-lg font-semibold mb-2 flex items-center gap-2">
                <FileText size={20} className="text-[var(--order-accent)]" />
                Upload expense invoice
              </h3>
              <p className="text-sm text-[var(--muted)] mb-6">
                Photo or PDF of a business expense. We will detect the date, description, amount, and purpose — then you confirm.
              </p>
              <Button
                type="button"
                disabled={recognizing}
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload size={18} className="mr-2 inline" />
                {recognizing ? 'Reading invoice…' : 'Choose file to upload'}
              </Button>
            </Card>
          ) : (
            <Card className="p-4 sm:p-6">
              <h3 className="text-lg font-semibold mb-1">Review recognized details</h3>
              <p className="text-sm text-[var(--muted)] mb-4">
                File: <span className="font-medium text-[var(--foreground)]">{preview.fileName}</span>
                {!preview.recognized && (
                  <span className="block mt-1 text-amber-700 dark:text-amber-400">
                    {preview.message ||
                      'Some fields could not be read automatically — please fill or correct them.'}
                  </span>
                )}
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6 items-start">
                <div>
                  <label className="text-xs text-[var(--muted)] mb-1 block">Date on bill</label>
                  <input
                    type="date"
                    value={form.expenseDate}
                    onChange={(e) => setForm({ ...form, expenseDate: e.target.value })}
                    className="form-input w-full px-3 py-2 rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs text-[var(--muted)] mb-1 block">Amount (₹)</label>
                  <input
                    type="number"
                    min={0}
                    step="0.01"
                    value={form.amount}
                    onChange={(e) => setForm({ ...form, amount: e.target.value })}
                    className="form-input w-full px-3 py-2 rounded-lg text-sm"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="text-xs text-[var(--muted)] mb-1 block">Description</label>
                  <input
                    type="text"
                    value={form.description}
                    onChange={(e) => setForm({ ...form, description: e.target.value })}
                    placeholder="Vendor or bill title"
                    className="form-input w-full px-3 py-2 rounded-lg text-sm"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="text-xs text-[var(--muted)] mb-1 block">Purpose (what it was used for)</label>
                  <input
                    type="text"
                    value={form.purpose}
                    onChange={(e) => setForm({ ...form, purpose: e.target.value })}
                    placeholder="e.g. vegetables, transport, gas, supplies"
                    className="form-input w-full px-3 py-2 rounded-lg text-sm"
                  />
                </div>
              </div>

              {!needsEdit ? (
                <div className="p-4 rounded-xl border border-[var(--border)] bg-[var(--background)] mb-4">
                  <p className="text-sm font-medium mb-3">Are these details correct?</p>
                  <div className="flex flex-wrap gap-3">
                    <Button type="button" disabled={saving} onClick={() => saveInvoice()}>
                      <CheckCircle2 size={16} className="mr-1.5 inline" />
                      Yes, correct — save
                    </Button>
                    <button
                      type="button"
                      onClick={() => setNeedsEdit(true)}
                      className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl border border-[var(--border)] text-sm font-medium hover:bg-[var(--sidebar-hover)]"
                    >
                      <XCircle size={16} />
                      No, let me edit
                    </button>
                    <button type="button" onClick={resetFlow} className="text-sm text-[var(--muted)] hover:underline">
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div className="p-4 rounded-xl border border-amber-500/40 bg-amber-500/5 mb-4">
                  <p className="text-sm mb-3">Update the fields above, then save the corrected invoice.</p>
                  <div className="flex flex-wrap gap-3">
                    <Button type="button" disabled={saving} onClick={() => saveInvoice()}>
                      {saving ? 'Saving…' : 'Save corrected details'}
                    </Button>
                    <button type="button" onClick={resetFlow} className="text-sm text-[var(--muted)] hover:underline">
                      Cancel
                    </button>
                  </div>
                </div>
              )}

              <dl className="text-sm grid grid-cols-2 gap-2 pt-4 border-t border-[var(--border)] text-[var(--muted)]">
                <dt>Amount preview</dt>
                <dd className="font-medium text-[var(--foreground)]">
                  {form.amount ? formatCurrency(Number(form.amount)) : '—'}
                </dd>
              </dl>
            </Card>
          )}

          {error && (
            <p className="mt-4 text-sm text-[var(--danger)]">{error}</p>
          )}

          {savedMsg && (
            <div className="mt-4 p-4 rounded-xl bg-[var(--primary-light)] text-sm flex gap-2">
              <CheckCircle2 size={18} className="text-[var(--primary)] shrink-0" />
              <p>{savedMsg}</p>
            </div>
          )}
        </div>

        <Card className="p-4 sm:p-6 lg:p-8 flex flex-col min-w-0 max-h-[22rem]">
          <h3 className="text-lg font-semibold mb-2 shrink-0">Split payments pending</h3>
          <p className="text-sm text-[var(--muted)] mb-4 shrink-0">
            Orders with a remaining balance after a partial payment
            {partialCount > 0 ? ` · ${partialCount} open` : ''}
          </p>
          <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain pr-1 -mr-1">
            <PartialPaymentsPanel
              embedded
              enquiries={enquiries}
              onUpdated={async (updated) => {
                patchEnquiry(updated);
                await refresh();
              }}
            />
          </div>
        </Card>
      </div>

      <div className="mb-10">
        <ExpenseBillsPanel
          items={expenseItems}
          highlightId={uploadId}
          onChanged={async () => {
            await refresh();
            if (uploadId) navigate('/invoices', { replace: true });
          }}
        />
      </div>
    </>
  );
}
