import { useState } from 'react';
import { PageHeader, Card, Button } from '../components/Layout';
import { useAppData } from '../context/AppDataContext';
import { useCreateActionListener } from '../hooks/useCreateActionListener';
import { createVendor, deleteVendor } from '../api/client';

const CATEGORIES = [
  'Marriage Halls', 'Event Organizers', 'Decorators', 'Photographers',
  'DJs', 'Vegetable Suppliers', 'Rice Suppliers', 'Transport Providers',
];

export default function VendorsPage() {
  const { vendors, refresh } = useAppData();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: '', businessName: '', phoneNumber: '', category: CATEGORIES[0], notes: '' });

  useCreateActionListener('vendor', () => setShowForm(true));

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    await createVendor({ ...form, businessName: form.businessName || null, notes: form.notes || null });
    setForm({ name: '', businessName: '', phoneNumber: '', category: CATEGORIES[0], notes: '' });
    setShowForm(false);
    refresh();
  }

  return (
    <>
      <PageHeader title="Vendor Directory" description={`${vendors.length} vendors — add & delete live`} />
      <div className="mb-6">
        <Button onClick={() => setShowForm(!showForm)}>{showForm ? 'Cancel' : '+ Add Vendor'}</Button>
      </div>
      {showForm && (
        <Card id="page-create-form" className="p-6 mb-6 animate-slide-up">
          <form onSubmit={handleAdd} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <input required placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="px-3 py-2 border rounded-lg" />
            <input placeholder="Business name" value={form.businessName} onChange={(e) => setForm({ ...form, businessName: e.target.value })} className="px-3 py-2 border rounded-lg" />
            <input required placeholder="Phone" value={form.phoneNumber} onChange={(e) => setForm({ ...form, phoneNumber: e.target.value })} className="px-3 py-2 border rounded-lg" />
            <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} className="form-select px-3 py-2 rounded-lg">
              {CATEGORIES.map((c) => <option key={c}>{c}</option>)}
            </select>
            <input placeholder="Notes" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} className="px-3 py-2 border rounded-lg md:col-span-2" />
            <Button type="submit">Save Vendor</Button>
          </form>
        </Card>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {vendors.map((v) => (
          <Card key={v.id} className="p-5">
            <div className="flex justify-between items-start">
              <div>
                <h3 className="font-semibold">{v.name}</h3>
                {v.businessName && <p className="text-sm text-[var(--muted)]">{v.businessName}</p>}
              </div>
              <span className="text-xs px-2 py-1 bg-[var(--primary-light)] rounded-full">{v.category}</span>
            </div>
            <p className="text-sm mt-2">{v.phoneNumber}</p>
            {v.notes && <p className="text-xs text-[var(--muted)] mt-1">{v.notes}</p>}
            <button type="button" onClick={() => { deleteVendor(v.id).then(refresh); }} className="text-xs text-red-600 mt-3 hover:underline">Delete</button>
          </Card>
        ))}
      </div>
      {vendors.length === 0 && <p className="text-center text-[var(--muted)] py-8">No vendors yet. Add one above.</p>}
    </>
  );
}
