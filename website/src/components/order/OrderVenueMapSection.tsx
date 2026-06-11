import { useEffect, useState } from 'react';
import { MapPinned } from 'lucide-react';
import { updateEnquiry } from '../../api/client';
import { normalizeMapUrl, qrCodeDataUrl } from '../../utils/qrCode';
import { serializeOrderNotes, type OrderExtras } from '../../utils/orderNotes';
import { Button } from '../Layout';

export function OrderVenueMapSection({
  orderId,
  extras,
  onRefresh,
}: {
  orderId: string;
  extras: OrderExtras;
  onRefresh: () => void;
}) {
  const [value, setValue] = useState(extras.venueMapLink ?? '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    setValue(extras.venueMapLink ?? '');
  }, [extras.venueMapLink]);

  async function save() {
    setError('');
    const trimmed = value.trim();
    if (trimmed && !normalizeMapUrl(trimmed)) {
      setError('Enter a valid Google Maps link (https://…).');
      return;
    }

    setSaving(true);
    try {
      const merged: OrderExtras = {
        ...extras,
        venueMapLink: trimmed || null,
      };
      await updateEnquiry(orderId, { notes: serializeOrderNotes(merged) });
      await onRefresh();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="order-section">
      <div className="order-section-head">
        <div className="order-section-title">
          <span className="order-section-icon order-section-icon--gold">
            <MapPinned size={18} />
          </span>
          Venue map link
        </div>
      </div>
      <p className="order-section-sub">
        Paste a Google Maps link for the event venue. A QR code is printed at the bottom of the{' '}
        <strong>kitchen copy</strong> so staff can scan for directions.
      </p>

      <label className="block text-xs font-semibold uppercase tracking-wide text-[var(--order-accent)] mb-1.5">
        Google Maps URL
      </label>
      <input
        type="url"
        value={value}
        onChange={(e) => {
          setValue(e.target.value);
          setError('');
        }}
        placeholder="https://maps.google.com/… or https://maps.app.goo.gl/…"
        className="form-input w-full px-3 py-2.5 rounded-lg text-sm mb-2"
      />
      {error && <p className="text-sm text-red-600 mb-3">{error}</p>}

      <Button type="button" onClick={save} disabled={saving} className="!py-2 !px-4 text-sm">
        {saving ? 'Saving…' : 'Save map link'}
      </Button>
    </div>
  );
}

export function VenueMapQrPrint({ mapLink }: { mapLink: string | null | undefined }) {
  const [qrSrc, setQrSrc] = useState<string | null>(null);
  const url = normalizeMapUrl(mapLink ?? '');

  useEffect(() => {
    if (!url) {
      setQrSrc(null);
      return;
    }
    let cancelled = false;
    qrCodeDataUrl(url, 220).then((dataUrl) => {
      if (!cancelled) setQrSrc(dataUrl);
    });
    return () => {
      cancelled = true;
    };
  }, [url]);

  if (!url || !qrSrc) return null;

  return (
    <div className="mt-8 border border-[var(--border-strong)] overflow-hidden">
      <div className="copy-grid-meta font-bold text-center border-b border-[var(--border)] bg-[var(--table-header-bg)]">
        Venue — scan for directions
      </div>
      <div className="px-4 py-6 text-center">
        <img
          src={qrSrc}
          alt="QR code for venue map"
          width={220}
          height={220}
          className="mx-auto block"
        />
        <p className="text-xs text-[var(--muted)] mt-4 break-all max-w-md mx-auto">{url}</p>
      </div>
    </div>
  );
}
