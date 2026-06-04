import { useMemo, useState } from 'react';
import { PageHeader, EmptyState, Card, Button } from '../components/Layout';
import { useAppData } from '../context/AppDataContext';
import { createDish } from '../api/client';
import { useCreateActionListener } from '../hooks/useCreateActionListener';
import { SearchInput, FilterChips } from '../components/ui';

const CATEGORIES = [
  { id: 'ALL', label: 'All' },
  { id: 'South Indian', label: 'South Indian' },
  { id: 'North Indian', label: 'North Indian' },
  { id: 'Chinese', label: 'Chinese' },
  { id: 'Snacks', label: 'Snacks' },
  { id: 'Desserts', label: 'Desserts' },
  { id: 'Beverages', label: 'Beverages' },
];

const ADD_CATEGORIES = CATEGORIES.filter((c) => c.id !== 'ALL');

export default function DishesPage() {
  const { dishes, refresh } = useAppData();
  const [search, setSearch] = useState('');
  const [cat, setCat] = useState('ALL');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: '', category: 'South Indian', price: 0, description: '' });

  useCreateActionListener('dish', () => setShowForm(true));

  const filtered = useMemo(() => {
    return dishes.filter((d) => {
      const matchCat = cat === 'ALL' || d.category === cat;
      const matchSearch = !search || d.name.toLowerCase().includes(search.toLowerCase());
      return matchCat && matchSearch;
    });
  }, [dishes, search, cat]);

  const grouped = filtered.reduce<Record<string, typeof dishes>>((acc, d) => {
    (acc[d.category] ||= []).push(d);
    return acc;
  }, {});

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    await createDish({
      name: form.name,
      category: form.category,
      price: form.price,
      description: form.description || undefined,
    });
    setForm({ name: '', category: 'South Indian', price: 0, description: '' });
    setShowForm(false);
    refresh();
  }

  return (
    <>
      <PageHeader title="Cuisine" description={`${dishes.length} menu items — manage cuisine types and menu catalog`} />
      <div className="mb-6">
        <Button onClick={() => setShowForm(!showForm)}>{showForm ? 'Cancel' : '+ Add Extra Dish'}</Button>
      </div>
      {showForm && (
        <Card id="page-create-form" className="p-6 mb-6">
          <form onSubmit={handleAdd} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <input required placeholder="Dish name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="px-3 py-2 border rounded-lg" />
            <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} className="form-select px-3 py-2 rounded-lg">
              {ADD_CATEGORIES.map((c) => <option key={c.id} value={c.id}>{c.label}</option>)}
            </select>
            <input required type="number" placeholder="Price (₹)" value={form.price || ''} onChange={(e) => setForm({ ...form, price: Number(e.target.value) })} className="px-3 py-2 border rounded-lg" />
            <input placeholder="Description (optional)" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="px-3 py-2 border rounded-lg" />
            <Button type="submit">Save to menu</Button>
          </form>
        </Card>
      )}
      <div className="flex flex-col lg:flex-row lg:items-center gap-4 mb-6">
        <SearchInput value={search} onChange={setSearch} placeholder="Search dishes by name..." />
        <FilterChips options={CATEGORIES} selected={cat} onSelect={setCat} />
      </div>
      {filtered.length === 0 ? (
        <EmptyState message="No dishes found." />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {Object.entries(grouped).map(([category, items]) => (
            <Card key={category} className="p-5">
              <h3 className="font-semibold text-[var(--primary-dark)] mb-3">{category}</h3>
              <ul className="space-y-2">
                {items.map((d) => (
                  <li key={d.id} className="flex justify-between text-sm py-1 border-b border-[var(--border)] last:border-0">
                    <span>{d.name}</span>
                    <span className="font-medium">₹{d.price}</span>
                  </li>
                ))}
              </ul>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
