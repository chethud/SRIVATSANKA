import { useCallback, useEffect, useMemo, useState } from 'react';
import { Pencil, Plus, Trash2, X } from 'lucide-react';
import { PageHeader, Card, Button, EmptyState } from '../components/Layout';
import { useAppData } from '../context/AppDataContext';
import { useCreateActionListener } from '../hooks/useCreateActionListener';
import { usePageSearch } from '../context/PageSearchContext';
import {
  addVendorCategory,
  createVendor,
  deleteVendor,
  fetchVendorCategories,
  updateVendor,
  type Vendor,
} from '../api/client';
import {
  categoriesFromVendors,
  mergeVendorCategories,
  pickCategoryValue,
  readStoredVendorCategories,
  storeVendorCategory,
} from '../utils/vendorCategories';

type VendorForm = {
  name: string;
  businessName: string;
  phones: string[];
  category: string;
  newCategory: string;
  notes: string;
};

function emptyForm(categories: string[]): VendorForm {
  return {
    name: '',
    businessName: '',
    phones: [''],
    category: categories[0] ?? '',
    newCategory: '',
    notes: '',
  };
}

function vendorPhones(v: Vendor): string[] {
  if (v.phoneNumbers && v.phoneNumbers.length > 0) return v.phoneNumbers;
  return v.phoneNumber ? [v.phoneNumber] : [];
}

export default function VendorsPage() {
  const { vendors, refresh } = useAppData();
  const [apiCategories, setApiCategories] = useState<string[] | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('ALL');
  const [form, setForm] = useState<VendorForm>(() => emptyForm(mergeVendorCategories()));

  const categoryOptions = useMemo(
    () =>
      mergeVendorCategories(
        apiCategories ?? [],
        categoriesFromVendors(vendors),
        readStoredVendorCategories(),
      ),
    [apiCategories, vendors],
  );

  const loadCategories = useCallback(async () => {
    try {
      const rows = await fetchVendorCategories();
      setApiCategories(rows);
    } catch {
      setApiCategories(null);
    }
  }, []);

  useEffect(() => {
    void loadCategories();
  }, [loadCategories]);

  useEffect(() => {
    setForm((prev) => ({
      ...prev,
      category: pickCategoryValue(prev.category, categoryOptions),
    }));
  }, [categoryOptions]);

  useCreateActionListener('vendor', () => {
    setEditingId(null);
    setForm(emptyForm(categoryOptions));
    setShowForm(true);
  });
  usePageSearch('Search vendors by name or business...', search, setSearch);

  const categoryFilterOptions = useMemo(() => {
    const used = Array.from(new Set(vendors.map((v) => v.category).filter(Boolean))).sort((a, b) =>
      a.localeCompare(b),
    );
    return [{ id: 'ALL', label: 'All types' }, ...used.map((c) => ({ id: c, label: c }))];
  }, [vendors]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    const digits = q.replace(/\D/g, '');
    return vendors.filter((v) => {
      if (categoryFilter !== 'ALL' && v.category !== categoryFilter) return false;
      if (!q) return true;
      const phones = vendorPhones(v).join(' ');
      const nameHay = [v.name, v.businessName ?? ''].join(' ').toLowerCase();
      if (nameHay.includes(q)) return true;
      if (v.category.toLowerCase().includes(q)) return true;
      if (digits && phones.replace(/\D/g, '').includes(digits)) return true;
      if ((v.notes ?? '').toLowerCase().includes(q)) return true;
      return false;
    });
  }, [vendors, search, categoryFilter]);

  function openCreate() {
    setEditingId(null);
    setForm(emptyForm(categoryOptions));
    setShowForm(true);
  }

  function openEdit(v: Vendor) {
    const phones = vendorPhones(v);
    setEditingId(v.id);
    setForm({
      name: v.name,
      businessName: v.businessName ?? '',
      phones: phones.length > 0 ? phones : [''],
      category: pickCategoryValue(v.category, categoryOptions),
      newCategory: '',
      notes: v.notes ?? '',
    });
    setShowForm(true);
  }

  function closeForm() {
    setShowForm(false);
    setEditingId(null);
    setForm(emptyForm(categoryOptions));
  }

  async function ensureCategoryStored(category: string) {
    const label = category.trim();
    if (!label) return;
    try {
      const rows = await addVendorCategory(label);
      setApiCategories(rows);
    } catch {
      storeVendorCategory(label);
    }
  }

  function setPhone(index: number, value: string) {
    setForm((prev) => ({
      ...prev,
      phones: prev.phones.map((p, i) => (i === index ? value : p)),
    }));
  }

  function addPhoneRow() {
    setForm((prev) => ({ ...prev, phones: [...prev.phones, ''] }));
  }

  function removePhoneRow(index: number) {
    setForm((prev) => ({
      ...prev,
      phones: prev.phones.length <= 1 ? [''] : prev.phones.filter((_, i) => i !== index),
    }));
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    const phones = form.phones.map((p) => p.trim()).filter(Boolean);
    if (!form.name.trim() || phones.length === 0) {
      alert('Enter vendor name and at least one phone number.');
      return;
    }
    let category = form.newCategory.trim() || form.category.trim();
    if (!category) {
      alert('Choose or add a business category.');
      return;
    }

    setSaving(true);
    try {
      if (form.newCategory.trim()) {
        category = form.newCategory.trim();
      }
      await ensureCategoryStored(category);

      const payload = {
        name: form.name.trim(),
        businessName: form.businessName.trim() || null,
        phoneNumbers: phones,
        phoneNumber: phones[0],
        category,
        notes: form.notes.trim() || null,
      };

      if (editingId) {
        await updateVendor(editingId, payload);
      } else {
        await createVendor(payload);
      }
      closeForm();
      await refresh();
      await loadCategories();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Could not save vendor.');
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(v: Vendor) {
    if (!window.confirm(`Delete vendor ${v.name}?`)) return;
    try {
      await deleteVendor(v.id);
      if (editingId === v.id) closeForm();
      await refresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Could not delete vendor.');
    }
  }

  return (
    <>
      <PageHeader
        title="Vendor Directory"
        description={`${filtered.length} of ${vendors.length} vendors — use search and type filter`}
      />

      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center">
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by name, business name, or phone"
          className="form-input min-w-0 flex-1 px-3 py-2.5 rounded-lg sm:max-w-xl"
          aria-label="Search vendors"
        />
        {categoryFilterOptions.length > 1 && (
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="form-select w-full shrink-0 px-3 py-2.5 rounded-lg sm:w-56"
            aria-label="Filter by business type"
          >
            {categoryFilterOptions.map((opt) => (
              <option key={opt.id} value={opt.id}>
                {opt.label}
              </option>
            ))}
          </select>
        )}
      </div>

      {showForm && (
        <Card id="page-create-form" className="p-6 mb-6 animate-slide-up">
          <h2 className="text-sm font-semibold mb-4">{editingId ? 'Edit vendor' : 'New vendor'}</h2>
          <form onSubmit={(ev) => void handleSave(ev)} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <input
              required
              placeholder="Contact name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="form-input px-3 py-2 rounded-lg"
            />
            <input
              placeholder="Business name"
              value={form.businessName}
              onChange={(e) => setForm({ ...form, businessName: e.target.value })}
              className="form-input px-3 py-2 rounded-lg"
            />

            <div className="md:col-span-2 space-y-2">
              <p className="text-xs font-semibold text-[var(--muted)] uppercase tracking-wide">Phone numbers</p>
              {form.phones.map((phone, index) => (
                <div key={index} className="flex gap-2">
                  <input
                    required={index === 0}
                    placeholder={index === 0 ? 'Primary phone' : 'Additional phone'}
                    value={phone}
                    onChange={(e) => setPhone(index, e.target.value)}
                    className="form-input flex-1 px-3 py-2 rounded-lg"
                  />
                  {form.phones.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removePhoneRow(index)}
                      className="px-3 py-2 rounded-lg border border-[var(--border)] hover:bg-[var(--sidebar-hover)]"
                      aria-label="Remove phone"
                    >
                      <X size={16} />
                    </button>
                  )}
                </div>
              ))}
              <button
                type="button"
                onClick={addPhoneRow}
                className="inline-flex items-center gap-1 text-xs font-semibold text-[var(--primary)] hover:underline"
              >
                <Plus size={14} /> Add another phone
              </button>
            </div>

            <div>
              <label className="text-xs font-semibold text-[var(--muted)] uppercase tracking-wide">Business type</label>
              <select
                required={!form.newCategory.trim()}
                value={pickCategoryValue(form.category, categoryOptions)}
                onChange={(e) => setForm({ ...form, category: e.target.value, newCategory: '' })}
                className="form-select w-full mt-1 px-3 py-2 rounded-lg"
              >
                {categoryOptions.length === 0 ? (
                  <option value="">Select business type</option>
                ) : (
                  categoryOptions.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))
                )}
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold text-[var(--muted)] uppercase tracking-wide">Or add new type</label>
              <input
                placeholder="New business category"
                value={form.newCategory}
                onChange={(e) => setForm({ ...form, newCategory: e.target.value })}
                className="form-input w-full mt-1 px-3 py-2 rounded-lg"
              />
            </div>

            <input
              placeholder="Notes"
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              className="form-input px-3 py-2 rounded-lg md:col-span-2"
            />
            <div className="flex gap-2 md:col-span-2">
              <Button type="submit" disabled={saving}>
                {saving ? 'Saving…' : editingId ? 'Update vendor' : 'Save vendor'}
              </Button>
              <button
                type="button"
                onClick={closeForm}
                className="px-4 py-2.5 text-sm border border-[var(--border)] rounded-xl hover:bg-[var(--sidebar-hover)]"
              >
                Cancel
              </button>
            </div>
          </form>
        </Card>
      )}

      {!showForm && (
        <div className="mb-4">
          <button
            type="button"
            onClick={openCreate}
            className="text-sm font-semibold text-[var(--primary)] hover:underline"
          >
            + Add vendor
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 grid-cards-equal">
        {filtered.map((v) => (
          <Card key={v.id} className="card-tile p-5">
            <div className="min-w-0 space-y-1">
              <h3 className="font-semibold leading-snug line-clamp-2">{v.name}</h3>
              {v.businessName && (
                <p className="text-sm text-[var(--muted)] leading-snug line-clamp-2">{v.businessName}</p>
              )}
            </div>
            {v.category && (
              <span className="mt-2 inline-block max-w-full truncate rounded-full bg-[var(--primary-light)] px-2.5 py-1 text-xs">
                {v.category}
              </span>
            )}
            <div className="mt-3 flex-1 min-h-[2.5rem]">
              <ul className="space-y-1 text-sm tabular-nums">
                {vendorPhones(v).map((phone) => (
                  <li key={phone} className="break-all">{phone}</li>
                ))}
              </ul>
              {v.notes && (
                <p className="mt-2 text-xs leading-relaxed text-[var(--muted)] line-clamp-3">{v.notes}</p>
              )}
            </div>
            <div className="card-tile__foot flex items-center gap-3 border-t border-[var(--border)] pt-3">
              <button
                type="button"
                onClick={() => openEdit(v)}
                className="inline-flex items-center gap-1 text-xs font-semibold text-[var(--primary)] hover:underline"
              >
                <Pencil size={12} /> Edit
              </button>
              <button
                type="button"
                onClick={() => void handleDelete(v)}
                className="inline-flex items-center gap-1 text-xs font-semibold text-red-600 hover:underline"
              >
                <Trash2 size={12} /> Delete
              </button>
            </div>
          </Card>
        ))}
      </div>
      {filtered.length === 0 && (
        <EmptyState
          message={
            vendors.length === 0
              ? 'No vendors yet. Add one above.'
              : 'No vendors match your search or category filter.'
          }
        />
      )}
    </>
  );
}
