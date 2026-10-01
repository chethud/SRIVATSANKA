import {
  PAYMENT_MODE_OPTIONS,
  RECEIVED_ACCOUNT_SUGGESTIONS,
  type PaymentMode,
} from '../utils/paymentRecord';

export type PaymentRecordDraft = {
  paymentMode: PaymentMode | '';
  paidAt: string;
  paymentNotes: string;
  receivedAccount: string;
};

export function PaymentRecordFields({
  value,
  onChange,
  compact = false,
}: {
  value: PaymentRecordDraft;
  onChange: (next: PaymentRecordDraft) => void;
  compact?: boolean;
}) {
  const grid = compact ? 'grid grid-cols-1 gap-3' : 'grid grid-cols-1 sm:grid-cols-2 gap-3';

  return (
    <div className={grid}>
      <label className="block text-sm sm:col-span-2">
        <span className="text-[var(--muted)]">Payment mode</span>
        <select
          value={value.paymentMode}
          onChange={(e) => onChange({ ...value, paymentMode: e.target.value as PaymentMode | '' })}
          className="mt-1 w-full rounded-xl border border-[var(--border)] bg-[var(--background)] px-3 py-2"
        >
          <option value="">Select cash or online</option>
          {PAYMENT_MODE_OPTIONS.map((o) => (
            <option key={o.id} value={o.id}>{o.label}</option>
          ))}
        </select>
      </label>
      <label className="block text-sm">
        <span className="text-[var(--muted)]">Payment date</span>
        <input
          type="datetime-local"
          value={value.paidAt}
          onChange={(e) => onChange({ ...value, paidAt: e.target.value })}
          className="mt-1 w-full rounded-xl border border-[var(--border)] bg-[var(--background)] px-3 py-2"
        />
      </label>
      <label className="block text-sm">
        <span className="text-[var(--muted)]">Received in account</span>
        <input
          type="text"
          list="received-account-suggestions"
          value={value.receivedAccount}
          onChange={(e) => onChange({ ...value, receivedAccount: e.target.value })}
          placeholder="e.g. HDFC Current, Cash in hand"
          className="mt-1 w-full rounded-xl border border-[var(--border)] bg-[var(--background)] px-3 py-2"
        />
        <datalist id="received-account-suggestions">
          {RECEIVED_ACCOUNT_SUGGESTIONS.map((a) => (
            <option key={a} value={a} />
          ))}
        </datalist>
      </label>
      <label className="block text-sm sm:col-span-2">
        <span className="text-[var(--muted)]">Payment notes</span>
        <textarea
          rows={2}
          value={value.paymentNotes}
          onChange={(e) => onChange({ ...value, paymentNotes: e.target.value })}
          placeholder="Reference, UTR, who handed cash, etc."
          className="mt-1 w-full rounded-xl border border-[var(--border)] bg-[var(--background)] px-3 py-2 resize-y"
        />
      </label>
    </div>
  );
}

export function paymentPayloadExtras(draft: PaymentRecordDraft): {
  paymentMode?: string;
  receivedAccount?: string;
  notes?: string;
  paidAt?: string;
} {
  const out: {
    paymentMode?: string;
    receivedAccount?: string;
    notes?: string;
    paidAt?: string;
  } = {};
  if (draft.paymentMode) out.paymentMode = draft.paymentMode;
  if (draft.receivedAccount.trim()) out.receivedAccount = draft.receivedAccount.trim();
  if (draft.paymentNotes.trim()) out.notes = draft.paymentNotes.trim();
  if (draft.paidAt) {
    const dt = new Date(draft.paidAt);
    if (!Number.isNaN(dt.getTime())) out.paidAt = dt.toISOString();
  }
  return out;
}
