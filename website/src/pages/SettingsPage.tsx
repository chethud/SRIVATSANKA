import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { PageHeader, Card } from '../components/Layout';
import { useAppData } from '../context/AppDataContext';
import { useBrand } from '../context/BrandContext';
import { fetchWhatsAppStatus, seedDemoData, brandLogoSrc, type WhatsAppStatus } from '../api/client';
import { ErrorBanner } from '../components/ui';

export default function SettingsPage() {
  const { connected, stats, lastSync, refresh } = useAppData();
  const { customLogo, updatedAt, uploadBrandLogo } = useBrand();
  const [wa, setWa] = useState<WhatsAppStatus | null>(null);
  const [seeding, setSeeding] = useState(false);
  const [seedMsg, setSeedMsg] = useState('');
  const [logoUploading, setLogoUploading] = useState(false);
  const [logoError, setLogoError] = useState('');
  const [logoMsg, setLogoMsg] = useState('');
  const logoInputRef = useRef<HTMLInputElement>(null);

  async function loadDemoData() {
    setSeeding(true);
    setSeedMsg('');
    try {
      const r = await seedDemoData();
      setSeedMsg(
        `Loaded ${r.enquiries} enquiries (${r.menuLines ?? 0} menu lines), ${r.vendors} vendors, ${r.workers} workers, ${r.expenses} expenses.`,
      );
      await refresh();
    } catch {
      setSeedMsg('Failed to load demo data. Check API URL and redeploy Render.');
    } finally {
      setSeeding(false);
    }
  }

  useEffect(() => {
    if (connected) {
      fetchWhatsAppStatus().then(setWa).catch(() => setWa(null));
    }
  }, [connected, lastSync]);

  async function handleLogoChange(file: File | null) {
    if (!file) return;
    setLogoUploading(true);
    setLogoError('');
    setLogoMsg('');
    try {
      await uploadBrandLogo(file);
      setLogoMsg('Logo updated for all users on the live site.');
    } catch {
      setLogoError('Could not upload logo. Use JPG, PNG, WebP, GIF, or SVG under 5 MB.');
    } finally {
      setLogoUploading(false);
      if (logoInputRef.current) logoInputRef.current.value = '';
    }
  }

  return (
    <>
      <PageHeader title="Settings" description="Live connection status and integrations" />
      <ErrorBanner message={!connected ? 'API offline — start FastAPI on port 8000' : ''} />
      <div className="space-y-6 max-w-2xl">
        <Card className="p-6">
          <h3 className="font-semibold mb-4">System Status</h3>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-[var(--muted)]">API</dt>
              <dd className={connected ? 'text-[var(--logo-forest)] font-medium' : 'text-[var(--danger)]'}>{connected ? 'Connected' : 'Offline'}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-[var(--muted)]">New Enquiries</dt>
              <dd>{stats?.new_enquiries ?? '—'}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-[var(--muted)]">Menu Dishes</dt>
              <dd>{stats?.total_dishes ?? '—'}</dd>
            </div>
            <button type="button" onClick={() => refresh()} className="text-sm text-[var(--primary)] hover:underline mt-2">
              Force refresh now
            </button>
          </dl>
        </Card>

        <Card className="p-6">
          <h3 className="font-semibold mb-4">Business Profile</h3>
          <div className="space-y-4">
            <div>
              <label className="text-sm text-[var(--muted)] block mb-2">Business logo</label>
              <div className="flex flex-wrap items-center gap-4">
                <div className="w-20 h-20 rounded-xl border border-[var(--border)] bg-[var(--background)] flex items-center justify-center overflow-hidden">
                  <img
                    src={customLogo ? brandLogoSrc(updatedAt) : '/brand/logo-icon.svg?v=4'}
                    alt="Business logo"
                    className="max-w-full max-h-full object-contain p-1"
                  />
                </div>
                <div>
                  <input
                    ref={logoInputRef}
                    type="file"
                    accept="image/jpeg,image/png,image/webp,image/gif,image/svg+xml"
                    className="hidden"
                    onChange={(e) => void handleLogoChange(e.target.files?.[0] ?? null)}
                  />
                  <button
                    type="button"
                    disabled={!connected || logoUploading}
                    onClick={() => logoInputRef.current?.click()}
                    className="px-4 py-2 bg-[var(--primary)] text-white rounded-lg text-sm hover:bg-[var(--primary-hover)] disabled:opacity-50"
                  >
                    {logoUploading ? 'Uploading…' : 'Change logo'}
                  </button>
                  <p className="text-xs text-[var(--muted)] mt-2 max-w-sm">
                    Saved on the server — sidebar, login, and order copies update for every user on the live site.
                  </p>
                  {logoMsg && <p className="text-xs text-[var(--logo-forest)] mt-2">{logoMsg}</p>}
                  {logoError && <p className="text-xs text-[var(--danger)] mt-2">{logoError}</p>}
                </div>
              </div>
            </div>
            <div>
              <label className="text-sm text-[var(--muted)]">Business Name</label>
              <input type="text" defaultValue="SRIVATSANKA" className="form-input w-full mt-1 px-4 py-2 rounded-lg" readOnly />
              <p className="text-xs text-[var(--muted)] mt-1">Pure Veg Catering Services for all Occasions</p>
            </div>
            <div>
              <label className="text-sm text-[var(--muted)]">Owner Phone (WhatsApp alerts)</label>
              <input type="tel" defaultValue={wa?.owner_phone ?? '+91 78994 10254'} className="form-input w-full mt-1 px-4 py-2 rounded-lg" readOnly />
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <h3 className="font-semibold mb-4">Meta WhatsApp Cloud API</h3>
          {wa ? (
            <ul className="text-sm space-y-2 mb-4">
              <li className="flex justify-between">
                <span>Configured</span>
                <span className={wa.configured ? 'text-[var(--logo-forest)]' : 'text-[var(--chart-amber)]'}>{wa.configured ? 'Yes' : 'No — add tokens in whatsapp/.env'}</span>
              </li>
              <li className="flex justify-between"><span>Phone Number ID</span><span>{wa.phone_number_id_set ? 'Set' : 'Missing'}</span></li>
              <li className="flex justify-between"><span>Access Token</span><span>{wa.token_set ? 'Set' : 'Missing'}</span></li>
              <li className="flex justify-between"><span>Owner alerts to</span><span>{wa.owner_phone}</span></li>
            </ul>
          ) : (
            <p className="text-sm text-[var(--muted)] mb-4">Connect API to see live WhatsApp status.</p>
          )}
          <p className="text-sm text-[var(--muted)] mb-3">Webhook: <code>https://YOUR-DOMAIN/webhook</code></p>
          <p className="text-sm text-[var(--muted)] mb-4">Guide: <code>docs/META_WHATSAPP_SETUP.md</code></p>
          <Link to="/bot-tester" className="inline-block px-4 py-2 bg-[var(--primary)] text-white rounded-lg text-sm hover:bg-[var(--primary-hover)] mr-3">
            Open WhatsApp Chat
          </Link>
        </Card>

        <Card className="p-6">
          <h3 className="font-semibold mb-4">WhatsApp AI Agent</h3>
          <p className="text-sm text-[var(--muted)]">Set <code>GEMINI_API_KEY</code> in <code>whatsapp/.env</code> for AI conversations.</p>
        </Card>

        <Card className="p-6">
          <h3 className="font-semibold mb-4">Demo data (Vercel + Render)</h3>
          <p className="text-sm text-[var(--muted)] mb-4">
            Loads sample enquiries, converted orders, vendors, workers, and expenses into the live API.
            Safe to run again — replaces previous demo rows only.
          </p>
          {seedMsg && <p className="text-sm mb-3 text-[var(--foreground)]">{seedMsg}</p>}
          <button
            type="button"
            onClick={loadDemoData}
            disabled={!connected || seeding}
            className="px-4 py-2 bg-[var(--primary)] text-white rounded-lg text-sm hover:bg-[var(--primary-hover)] disabled:opacity-50"
          >
            {seeding ? 'Loading…' : 'Load demo data'}
          </button>
        </Card>

        <Card className="p-6">
          <h3 className="font-semibold mb-4">Notifications</h3>
          <label className="flex items-center gap-3 text-sm">
            <input type="checkbox" defaultChecked disabled />
            Instant notification on new WhatsApp enquiry (enabled in backend)
          </label>
          <label className="flex items-center gap-3 text-sm mt-3">
            <input type="checkbox" defaultChecked disabled />
            Callback reminder 15–20 min before preferred time (enabled in backend)
          </label>
        </Card>
      </div>
    </>
  );
}
