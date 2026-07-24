import { useMemo, useState } from 'react';
import { Plus } from 'lucide-react';
import { PageHeader, EmptyState, Card, Button } from '../components/Layout';
import { useAppData } from '../context/AppDataContext';
import { createDish } from '../api/client';
import { useCreateActionListener } from '../hooks/useCreateActionListener';
import { usePageSearch } from '../context/PageSearchContext';
import { MEAL_SESSIONS, isPresetMealSession, resolveSessionTabs } from '../utils/mealSessions';

const CUSTOM_OPTION = '__custom__';

export default function DishesPage() {
  const { dishes, refresh } = useAppData();
  const [search, setSearch] = useState('');
  const [cat, setCat] = useState('ALL');
  const [showForm, setShowForm] = useState(false);
  const [extraSessions, setExtraSessions] = useState<string[]>([]);
  const [addingSession, setAddingSession] = useState(false);
  const [newSessionName, setNewSessionName] = useState('');
  const [form, setForm] = useState({
    name: '',
    category: 'Breakfast',
    customCategory: '',
    description: '',
  });
  const [formError, setFormError] = useState('');

  useCreateActionListener('dish', () => {
    setShowForm(true);
    setForm((prev) => ({
      ...prev,
      category: cat !== 'ALL' ? cat : prev.category,
      customCategory: cat !== 'ALL' && !isPresetMealSession(cat) ? cat : '',
    }));
  });
  usePageSearch('Search dishes by name...', search, setSearch);

  useCreateActionListener('session', () => {
    setAddingSession(true);
    setNewSessionName('');
  });

  const catalogSessions = useMemo(
    () => resolveSessionTabs(extraSessions, dishes.map((d) => d.category)),
    [dishes, extraSessions],
  );

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

  const categorySelectValue =
    form.category === CUSTOM_OPTION
      ? CUSTOM_OPTION
      : isPresetMealSession(form.category) || catalogSessions.some((s) => s.id === form.category)
        ? form.category
        : CUSTOM_OPTION;

  function openAddDishForSession(session: string) {
    setForm({
      name: '',
      category: session,
      customCategory: isPresetMealSession(session) ? '' : session,
      description: '',
    });
    setShowForm(true);
    setFormError('');
  }

  function handleAddSession() {
    const name = newSessionName.trim();
    if (!name) return;
    const existing = catalogSessions.find((s) => s.id.toLowerCase() === name.toLowerCase());
    if (existing) {
      setCat(existing.id);
      openAddDishForSession(existing.id);
    } else {
      setExtraSessions((prev) => [...prev, name]);
      setCat(name);
      openAddDishForSession(name);
    }
    setAddingSession(false);
    setNewSessionName('');
  }

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    setFormError('');
    const category =
      categorySelectValue === CUSTOM_OPTION
        ? form.customCategory.trim() || form.category.trim()
        : form.category.trim();
    if (!category) {
      setFormError('Enter a session name (e.g. High Tea).');
      return;
    }
    try {
      await createDish({
        name: form.name,
        category,
        price: 0,
        description: form.description || undefined,
      });
      if (!isPresetMealSession(category)) {
        setExtraSessions((prev) =>
          prev.some((s) => s.toLowerCase() === category.toLowerCase()) ? prev : [...prev, category],
        );
      }
      setCat(category);
      setForm({ name: '', category: 'Breakfast', customCategory: '', description: '' });
      setShowForm(false);
      refresh();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Could not save dish.');
    }
  }

  return (
    <>
      <PageHeader title="Menu" description={`${dishes.length} dishes`} />

      <div id="page-add-session" className="order-session-tabs mb-4">
        <button
          type="button"
          onClick={() => setCat('ALL')}
          className={`order-session-tab ${cat === 'ALL' ? 'order-session-tab--active' : ''}`}
        >
          All
        </button>
        {catalogSessions.map((s) => (
          <button
            key={s.id}
            type="button"
            onClick={() => setCat(s.id)}
            className={`order-session-tab ${cat === s.id ? 'order-session-tab--active' : ''}`}
          >
            {s.label}
          </button>
        ))}
        {addingSession && (
          <div className="order-session-add-form">
            <input
              autoFocus
              value={newSessionName}
              onChange={(e) => setNewSessionName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleAddSession();
                if (e.key === 'Escape') {
                  setAddingSession(false);
                  setNewSessionName('');
                }
              }}
              placeholder="e.g. High Tea"
              className="order-session-add-input"
              maxLength={40}
            />
            <button
              type="button"
              onClick={handleAddSession}
              disabled={!newSessionName.trim()}
              className="order-session-tab order-session-tab--active"
            >
              Add
            </button>
            <button
              type="button"
              onClick={() => {
                setAddingSession(false);
                setNewSessionName('');
              }}
              className="order-session-tab"
            >
              Cancel
            </button>
          </div>
        )}
      </div>

      {showForm && (
        <Card id="page-create-form" className="p-6 mb-6">
          <form onSubmit={handleAdd} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <input
              required
              placeholder="Dish name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="px-3 py-2 border rounded-lg"
            />
            <select
              value={categorySelectValue}
              onChange={(e) => {
                const v = e.target.value;
                if (v === CUSTOM_OPTION) {
                  setForm({ ...form, category: CUSTOM_OPTION, customCategory: form.customCategory });
                } else {
                  setForm({ ...form, category: v, customCategory: '' });
                }
              }}
              className="form-select px-3 py-2 rounded-lg"
            >
              {MEAL_SESSIONS.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.label}
                </option>
              ))}
              {catalogSessions
                .filter((s) => !isPresetMealSession(s.id))
                .map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.label}
                  </option>
                ))}
              <option value={CUSTOM_OPTION}>+ New custom session…</option>
            </select>
            {categorySelectValue === CUSTOM_OPTION && (
              <input
                required
                placeholder="Custom session name (e.g. High Tea)"
                value={form.customCategory}
                onChange={(e) => setForm({ ...form, customCategory: e.target.value })}
                className="px-3 py-2 border rounded-lg md:col-span-2"
              />
            )}
            <input
              placeholder="Description (optional)"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              className="px-3 py-2 border rounded-lg md:col-span-2"
            />
            {formError && (
              <p className="text-sm text-red-600 md:col-span-2">{formError}</p>
            )}
            <div className="flex gap-2 md:col-span-2">
              <Button type="submit">Save to menu</Button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="px-4 py-2.5 text-sm border border-[var(--border)] rounded-xl hover:bg-[var(--sidebar-hover)]"
              >
                Cancel
              </button>
            </div>
          </form>
        </Card>
      )}

      {cat !== 'ALL' && (
        <div className="flex flex-col lg:flex-row lg:items-center gap-4 mb-6">
          <Button type="button" onClick={() => openAddDishForSession(cat)} className="!py-2 !px-4 text-sm">
            <Plus size={16} className="inline mr-1" /> Add dish to {cat}
          </Button>
        </div>
      )}

      {filtered.length === 0 ? (
        <EmptyState
          message={
            cat === 'ALL'
              ? 'No dishes found.'
              : `No dishes in ${cat} yet — use Add dish or New menu item.`
          }
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 items-start">
          {Object.entries(grouped).map(([category, items]) => (
            <Card key={category} className="p-5">
              <h3 className="font-semibold text-[var(--primary-dark)] mb-3">{category}</h3>
              <ul className="space-y-2">
                {items.map((d) => (
                  <li key={d.id} className="text-sm py-1 border-b border-[var(--border)] last:border-0">
                    {d.name}
                    {d.description && (
                      <span className="block text-xs text-[var(--muted)] mt-0.5">{d.description}</span>
                    )}
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
