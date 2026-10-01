import { useEffect, useMemo, useState } from 'react';
import { Plus, Pencil, Trash2, X } from 'lucide-react';
import { PageHeader, EmptyState, Card, Button } from '../components/Layout';
import { useAppData } from '../context/AppDataContext';
import { createDish, deleteDish, updateDish, type Dish } from '../api/client';
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
  const [saving, setSaving] = useState(false);
  const [editingDishId, setEditingDishId] = useState('');
  const [deletingId, setDeletingId] = useState('');

  useCreateActionListener('dish', () => {
    openAddDishForSession(cat !== 'ALL' ? cat : 'Breakfast');
  });
  usePageSearch('Search dishes by name...', search, setSearch);

  useCreateActionListener('session', () => {
    setAddingSession(true);
    setNewSessionName('');
  });

  useEffect(() => {
    if (!showForm) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        setShowForm(false);
        setEditingDishId('');
      }
    }
    document.addEventListener('keydown', onKey);
    return () => {
      document.body.style.overflow = prev;
      document.removeEventListener('keydown', onKey);
    };
  }, [showForm]);

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

  const categoryCards = useMemo(() => {
    const entries = Object.entries(grouped);
    if (cat !== 'ALL' && !grouped[cat] && !search) {
      return [[cat, []] as const];
    }
    return entries;
  }, [grouped, cat, search]);

  /** One session tab: use full grid width and two dish columns (like All’s left/right cards). */
  const singleSessionLayout = cat !== 'ALL';

  const categorySelectValue =
    form.category === CUSTOM_OPTION
      ? CUSTOM_OPTION
      : isPresetMealSession(form.category) || catalogSessions.some((s) => s.id === form.category)
        ? form.category
        : CUSTOM_OPTION;

  function openAddDishForSession(session: string) {
    setEditingDishId('');
    setForm({
      name: '',
      category: session,
      customCategory: isPresetMealSession(session) ? '' : session,
      description: '',
    });
    setShowForm(true);
    setFormError('');
  }

  function openEditDish(dish: Dish) {
    setEditingDishId(dish.id);
    setForm({
      name: dish.name,
      category: isPresetMealSession(dish.category) ? dish.category : CUSTOM_OPTION,
      customCategory: isPresetMealSession(dish.category) ? '' : dish.category,
      description: dish.description ?? '',
    });
    setShowForm(true);
    setFormError('');
  }

  async function handleDeleteDish(dish: Dish) {
    if (deletingId) return;
    const ok = window.confirm(
      `Delete "${dish.name}" from the menu?\n\nExisting orders keep their saved copies. This removes the dish from the catalog.`,
    );
    if (!ok) return;
    setDeletingId(dish.id);
    try {
      await deleteDish(dish.id);
      await refresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Could not delete the dish.');
    } finally {
      setDeletingId('');
    }
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
    setSaving(true);
    try {
      if (editingDishId) {
        await updateDish(editingDishId, {
          name: form.name,
          category,
          description: form.description || null,
        });
      } else {
        await createDish({
          name: form.name,
          category,
          price: 0,
          description: form.description || undefined,
        });
      }
      if (!isPresetMealSession(category)) {
        setExtraSessions((prev) =>
          prev.some((s) => s.toLowerCase() === category.toLowerCase()) ? prev : [...prev, category],
        );
      }
      setCat(category);
      setForm({ name: '', category: 'Breakfast', customCategory: '', description: '' });
      setEditingDishId('');
      setShowForm(false);
      refresh();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Could not save dish.');
    } finally {
      setSaving(false);
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
        {!addingSession ? (
          <button
            type="button"
            onClick={() => {
              setAddingSession(true);
              setNewSessionName('');
            }}
            className="order-session-tab order-session-tab--add"
          >
            <Plus size={14} /> Add session
          </button>
        ) : (
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
        <div
          id="page-create-form"
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="add-dish-title"
        >
          <button
            type="button"
            className="absolute inset-0 bg-black/40 border-0 cursor-pointer"
            aria-label="Close add dish"
            onClick={() => {
              setShowForm(false);
              setEditingDishId('');
            }}
          />
          <Card className="relative z-10 w-full max-w-lg p-6 shadow-[var(--shadow-lg)]">
            <div className="flex items-start justify-between gap-3 mb-4">
              <div>
                <h2 id="add-dish-title" className="text-lg font-semibold text-[var(--foreground)]">
                  {editingDishId ? 'Edit dish' : 'Add dish'}
                </h2>
                <p className="text-sm text-[var(--muted)] mt-0.5">
                  {categorySelectValue === CUSTOM_OPTION
                    ? 'Choose a session and dish name'
                    : `Session: ${form.category}`}
                </p>
              </div>
              <button
                type="button"
                onClick={() => {
              setShowForm(false);
              setEditingDishId('');
            }}
                className="inline-flex items-center justify-center w-9 h-9 rounded-lg border border-[var(--border)] text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--sidebar-hover)]"
                aria-label="Close"
              >
                <X size={16} />
              </button>
            </div>
            <form onSubmit={handleAdd} className="grid grid-cols-1 gap-4">
              <input
                required
                autoFocus
                placeholder="Dish name"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="form-input px-3 py-2.5 rounded-lg"
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
                className="form-select px-3 py-2.5 rounded-lg"
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
                  className="form-input px-3 py-2.5 rounded-lg"
                />
              )}
              <input
                placeholder="Description (optional)"
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                className="form-input px-3 py-2.5 rounded-lg"
              />
              {formError && <p className="text-sm text-[var(--danger)]">{formError}</p>}
              <div className="flex gap-2 justify-end pt-1">
                <button
                  type="button"
                  onClick={() => {
              setShowForm(false);
              setEditingDishId('');
            }}
                  className="px-4 py-2.5 text-sm border border-[var(--border)] rounded-xl hover:bg-[var(--sidebar-hover)]"
                >
                  Cancel
                </button>
                <Button type="submit" disabled={saving}>
                  {saving ? 'Saving…' : editingDishId ? 'Save changes' : 'Save to menu'}
                </Button>
              </div>
            </form>
          </Card>
        </div>
      )}

      {categoryCards.length === 0 ? (
        <EmptyState
          message={
            cat === 'ALL'
              ? 'No dishes found.'
              : `No dishes in ${cat} yet — use Add dish on the session card.`
          }
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 grid-cards-equal">
          {categoryCards.map(([category, items]) => (
            <Card
              key={category}
              className={`card-tile p-5${singleSessionLayout ? ' md:col-span-2 xl:col-span-3' : ''}`}
            >
              <div className="flex items-center justify-between gap-2 mb-3 shrink-0">
                <h3 className="font-semibold text-[var(--primary-dark)]">{category}</h3>
                <button
                  type="button"
                  onClick={() => openAddDishForSession(category)}
                  className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-semibold rounded-lg border border-[var(--border)] text-[var(--primary)] hover:bg-[var(--primary-light)] hover:border-[var(--primary)]"
                >
                  <Plus size={14} /> Add dish
                </button>
              </div>
              <div className="card-tile__body">
              {items.length === 0 ? (
                <p className="text-sm text-[var(--muted)] py-2 min-h-[4rem]">No dishes yet in this session.</p>
              ) : (
                <ul
                  className={
                    singleSessionLayout && items.length > 0
                      ? 'flex-1 min-h-[4rem] grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2'
                      : 'space-y-2 flex-1 min-h-[4rem]'
                  }
                >
                  {items.map((d) => (
                    <li
                      key={d.id}
                      className="flex items-start justify-between gap-2 text-sm py-1 border-b border-[var(--border)] last:border-0"
                    >
                      <div className="min-w-0 flex-1">
                        <span className="break-words">{d.name}</span>
                        {d.description && (
                          <span className="block text-xs text-[var(--muted)] mt-0.5">{d.description}</span>
                        )}
                      </div>
                      <div className="flex items-center gap-1 shrink-0">
                        <button
                          type="button"
                          onClick={() => openEditDish(d)}
                          className="inline-flex items-center justify-center p-1.5 rounded-lg text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--sidebar-hover)]"
                          aria-label={`Edit ${d.name}`}
                        >
                          <Pencil size={14} />
                        </button>
                        <button
                          type="button"
                          disabled={deletingId === d.id}
                          onClick={() => void handleDeleteDish(d)}
                          className="inline-flex items-center justify-center p-1.5 rounded-lg text-red-600 hover:bg-red-50 disabled:opacity-60"
                          aria-label={`Delete ${d.name}`}
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
