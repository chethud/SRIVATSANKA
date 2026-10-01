import { useEffect, useState } from 'react';
import { PageHeader, Card, Button } from '../components/Layout';
import { useAppData } from '../context/AppDataContext';
import { FONT_SCALE_OPTIONS, useTheme } from '../context/ThemeContext';
import { fetchWhatsAppStatus, updateOwnerPhone, formatPhoneDisplay, normalizePhoneInput, type WhatsAppStatus } from '../api/client';
import { ErrorBanner } from '../components/ui';
import { BRAND_NAME, BRAND_TAGLINE } from '../brand';

function ApiStatusChip({
  connected,
  onRefresh,
}: {
  connected: boolean;
  onRefresh: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onRefresh}
      className="inline-flex items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--card)] px-3 py-1.5 text-xs font-medium text-[var(--foreground)] shadow-[var(--shadow-sm)] hover:border-[var(--primary)]/40 transition-colors"
      title="Refresh dashboard data"
    >
      <span
        className={`h-2 w-2 rounded-full shrink-0 ${connected ? 'bg-[var(--success-text)]' : 'bg-[var(--danger)]'}`}
        aria-hidden
      />
      API {connected ? 'Connected' : 'Offline'}
    </button>
  );
}

export default function SettingsPage() {
  const { connected, refresh } = useAppData();
  const { fontScale, setFontScale } = useTheme();
  const [wa, setWa] = useState<WhatsAppStatus | null>(null);
  const [ownerPhone, setOwnerPhone] = useState('');
  const [editingOwnerPhone, setEditingOwnerPhone] = useState(false);
  const [savingOwnerPhone, setSavingOwnerPhone] = useState(false);
  const [ownerPhoneMsg, setOwnerPhoneMsg] = useState('');

  useEffect(() => {
    if (connected) {
      fetchWhatsAppStatus()
        .then((status) => {
          setWa(status);
          if (!editingOwnerPhone) {
            setOwnerPhone(formatPhoneDisplay(status.owner_phone) || status.owner_phone);
          }
        })
        .catch(() => setWa(null));
    }
  }, [connected, editingOwnerPhone]);

  async function saveOwnerPhone() {
    setSavingOwnerPhone(true);
    setOwnerPhoneMsg('');
    try {
      const result = await updateOwnerPhone(normalizePhoneInput(ownerPhone) || ownerPhone);
      setOwnerPhone(formatPhoneDisplay(result.owner_phone));
      setWa((prev) => (prev ? { ...prev, owner_phone: result.owner_phone } : prev));
      setEditingOwnerPhone(false);
      setOwnerPhoneMsg('Owner alert number saved. New enquiries will notify this WhatsApp.');
    } catch (err) {
      setOwnerPhoneMsg(err instanceof Error ? err.message : 'Could not save owner phone.');
    } finally {
      setSavingOwnerPhone(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Settings"
        description="Business profile and display preferences"
        actions={<ApiStatusChip connected={connected} onRefresh={() => void refresh()} />}
      />
      <ErrorBanner message={!connected ? 'API offline — start FastAPI on port 8001' : ''} />
      <div className="space-y-4 max-w-2xl">
        <Card className="p-6">
          <h3 className="font-semibold mb-4">Business Profile</h3>
          <div className="space-y-4">
            <div>
              <label className="text-sm text-[var(--muted)]">Business Name</label>
              <input type="text" defaultValue={BRAND_NAME} className="form-input w-full mt-1 px-4 py-2 rounded-lg" readOnly />
              <p className="text-xs text-[var(--muted)] mt-1">{BRAND_TAGLINE}</p>
            </div>
            <div>
              <label className="text-sm text-[var(--muted)]" htmlFor="owner-phone">
                Owner Phone (WhatsApp alerts)
              </label>
              <div className="mt-1 flex flex-wrap gap-2">
                <input
                  id="owner-phone"
                  type="tel"
                  value={ownerPhone}
                  readOnly={!editingOwnerPhone}
                  onChange={(e) => setOwnerPhone(e.target.value)}
                  placeholder="919945607074"
                  className={`form-input flex-1 min-w-[12rem] px-4 py-2 rounded-lg ${
                    editingOwnerPhone ? '' : 'opacity-90'
                  }`}
                />
                {editingOwnerPhone ? (
                  <>
                    <Button type="button" onClick={() => void saveOwnerPhone()} disabled={!connected || savingOwnerPhone}>
                      {savingOwnerPhone ? 'Saving…' : 'Save'}
                    </Button>
                    <button
                      type="button"
                      onClick={() => {
                        setEditingOwnerPhone(false);
                        setOwnerPhoneMsg('');
                        setOwnerPhone(formatPhoneDisplay(wa?.owner_phone || '') || wa?.owner_phone || '');
                      }}
                      className="px-4 py-2 text-sm border border-[var(--border)] rounded-xl hover:bg-[var(--sidebar-hover)]"
                    >
                      Cancel
                    </button>
                  </>
                ) : (
                  <button
                    type="button"
                    onClick={() => {
                      setEditingOwnerPhone(true);
                      setOwnerPhoneMsg('');
                    }}
                    disabled={!connected}
                    className="px-4 py-2 text-sm border border-[var(--border)] rounded-xl hover:bg-[var(--sidebar-hover)] disabled:opacity-50"
                  >
                    Edit
                  </button>
                )}
              </div>
              <p className="text-xs text-[var(--muted)] mt-1">
                New enquiry and callback alerts are sent to this number.
              </p>
              {ownerPhoneMsg && <p className="text-sm mt-2 text-[var(--foreground)]">{ownerPhoneMsg}</p>}
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <h3 className="font-semibold text-sm">Display</h3>
              <p className="text-xs text-[var(--muted)] mt-0.5">Font size — saved on this device</p>
            </div>
            <div className="flex flex-wrap gap-1.5" role="group" aria-label="Font size">
              {FONT_SCALE_OPTIONS.map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => setFontScale(opt.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors ${
                    fontScale === opt.id
                      ? 'bg-[var(--primary)] text-white border-[var(--primary)]'
                      : 'bg-[var(--background)] text-[var(--foreground)] border-[var(--border)] hover:border-[var(--primary)]'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        </Card>
      </div>
    </>
  );
}
