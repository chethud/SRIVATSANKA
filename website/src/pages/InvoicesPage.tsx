import { useRef, useState } from 'react';
import { useCreateActionListener } from '../hooks/useCreateActionListener';
import { Link } from 'react-router-dom';
import { BarChart3, CheckCircle2, Upload } from 'lucide-react';
import { PageHeader, Card } from '../components/Layout';
import { BrandLogo } from '../components/BrandLogo';
import { useAppData } from '../context/AppDataContext';
import { uploadExpenseInvoice, formatCurrency } from '../api/client';

export default function InvoicesPage() {
  const { refresh } = useAppData();
  const [uploading, setUploading] = useState(false);
  const [msg, setMsg] = useState('');
  const [lastSuccess, setLastSuccess] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useCreateActionListener('invoice', () => fileInputRef.current?.click());

  async function handleUpload(file: File) {
    setUploading(true);
    setMsg('');
    setLastSuccess(false);
    try {
      const result = await uploadExpenseInvoice(file);
      const desc = result.notes || 'Expense';
      const amt = result.amount != null ? formatCurrency(result.amount) : 'amount not detected';
      setMsg(
        result.recognized
          ? `Recognized: ${desc} — ${amt}. This is now in Analytics.`
          : `Saved. ${result.notes || 'Add GEMINI_API_KEY in whatsapp/.env to auto-read bills.'}`,
      );
      setLastSuccess(result.recognized);
      refresh();
    } catch {
      setMsg('Upload failed. Make sure FastAPI is running on port 8000.');
    } finally {
      setUploading(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Invoices"
        description="Use Upload invoice in the header — expense bills are read by AI and appear in Analytics."
      />

      <input
        ref={fileInputRef}
        type="file"
        accept=".jpg,.jpeg,.png,.webp,.pdf"
        className="hidden"
        disabled={uploading}
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) handleUpload(f);
          e.target.value = '';
        }}
      />

      <Card id="page-create-form" className="p-8 max-w-xl mx-auto text-center">
        <BrandLogo variant="card" className="mx-auto mb-6 max-w-[220px]" />
        <h3 className="text-lg font-semibold mb-2">Expense invoices</h3>
        <p className="text-sm text-[var(--muted)] mb-6">
          Photo or PDF of any business expense (vegetables, transport, supplies, etc.).
          Click <strong>Upload invoice</strong> in the top bar to choose a file.
        </p>

        <div className="inline-flex items-center gap-2 px-4 py-3 rounded-xl border border-dashed border-[var(--border)] text-sm text-[var(--muted)]">
          <Upload size={18} className="text-[var(--order-accent)]" />
          {uploading ? 'Reading invoice…' : 'Ready — use header Upload invoice'}
        </div>

        {msg && (
          <div
            className={`mt-6 p-4 rounded-xl text-sm text-left flex gap-3 ${
              msg.includes('failed')
                ? 'bg-[var(--danger-bg)] text-[var(--danger)]'
                : 'bg-[var(--primary-light)] text-[var(--foreground)]'
            }`}
          >
            {lastSuccess && <CheckCircle2 size={20} className="shrink-0 text-[var(--primary)]" />}
            <p>{msg}</p>
          </div>
        )}

        <Link
          to="/analytics"
          className="inline-flex items-center gap-2 mt-8 text-sm font-medium text-[var(--primary)] hover:underline"
        >
          <BarChart3 size={18} />
          View expenses & profit in Analytics →
        </Link>
      </Card>
    </>
  );
}
