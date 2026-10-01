import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ArrowLeft, ImagePlus, Upload } from 'lucide-react';
import { PageHeader, Card, Button, EmptyState } from '../components/Layout';
import { ErrorBanner } from '../components/ui';
import { useCreateActionListener } from '../hooks/useCreateActionListener';
import {
  deleteEventPhoto,
  fetchEventPhotoAlbums,
  uploadEventPhotos,
  type EventPhoto,
  type EventPhotoAlbum,
} from '../api/client';
import { MAX_PHOTOS_PER_EVENT, PHOTO_EVENTS, type PhotoEventDef } from '../data/photoEvents';

const LOCAL_KEY = 'kannans_event_photos_v1';
const EVENTS_KEY = 'kannans_photo_event_types_v1';
const DEFAULT_COVER = PHOTO_EVENTS[0].coverUrl;

function readLocalAlbums(): EventPhotoAlbum[] {
  try {
    const raw = localStorage.getItem(LOCAL_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as EventPhotoAlbum[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeLocalAlbums(albums: EventPhotoAlbum[]) {
  localStorage.setItem(LOCAL_KEY, JSON.stringify(albums));
}

function readCustomEvents(): PhotoEventDef[] {
  try {
    const raw = localStorage.getItem(EVENTS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as PhotoEventDef[];
    return Array.isArray(parsed) ? parsed.filter((e) => e?.eventType?.trim()) : [];
  } catch {
    return [];
  }
}

function writeCustomEvents(events: PhotoEventDef[]) {
  localStorage.setItem(EVENTS_KEY, JSON.stringify(events));
}

function mergeCatalog(extra: PhotoEventDef[]): PhotoEventDef[] {
  const seen = new Set(PHOTO_EVENTS.map((e) => e.eventType.toLowerCase()));
  const extras = extra.filter((e) => {
    const key = e.eventType.trim().toLowerCase();
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
  return [...PHOTO_EVENTS, ...extras];
}

function albumsForEvents(stored: EventPhotoAlbum[], catalog: PhotoEventDef[]): EventPhotoAlbum[] {
  const byType = new Map(stored.map((a) => [a.eventType, a]));
  return catalog.map((event) => {
    const found = byType.get(event.eventType);
    const photos = (found?.photos ?? []).slice(0, MAX_PHOTOS_PER_EVENT);
    return { eventType: event.eventType, count: photos.length, photos };
  });
}

function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ''));
    reader.onerror = () => reject(new Error('Could not read image'));
    reader.readAsDataURL(file);
  });
}

export default function PhotosPage() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [catalog, setCatalog] = useState<PhotoEventDef[]>(() => mergeCatalog(readCustomEvents()));
  const [albums, setAlbums] = useState<EventPhotoAlbum[]>(() => albumsForEvents([], mergeCatalog(readCustomEvents())));
  const [selected, setSelected] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [newEventName, setNewEventName] = useState('');
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState('');
  const [useLocal, setUseLocal] = useState(false);

  useCreateActionListener('photoEvent', () => {
    setSelected(null);
    setShowForm(true);
  });

  const load = useCallback(async () => {
    const nextCatalog = mergeCatalog(readCustomEvents());
    setCatalog(nextCatalog);
    try {
      const data = await fetchEventPhotoAlbums();
      setAlbums(albumsForEvents(data.albums, nextCatalog));
      setUseLocal(false);
      setError('');
    } catch {
      setAlbums(albumsForEvents(readLocalAlbums(), nextCatalog));
      setUseLocal(true);
      setError('');
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const eventCards = useMemo(() => {
    return catalog.map((event) => {
      const album = albums.find((a) => a.eventType === event.eventType);
      return {
        ...event,
        count: album?.count ?? 0,
        photos: album?.photos ?? [],
        coverUrl: album?.photos[0]?.url || event.coverUrl || DEFAULT_COVER,
      };
    });
  }, [albums, catalog]);

  const album = eventCards.find((a) => a.eventType === selected) ?? null;
  const remaining = album ? Math.max(0, MAX_PHOTOS_PER_EVENT - album.count) : 0;

  async function addFiles(list: FileList | File[] | null) {
    if (!selected || !list) return;
    const files = Array.from(list).filter((f) => f.type.startsWith('image/'));
    if (!files.length) {
      setError('Choose image files (JPG, PNG, WEBP, or GIF).');
      return;
    }
    if (remaining <= 0) {
      setError(`Each event can have at most ${MAX_PHOTOS_PER_EVENT} photos.`);
      return;
    }
    const batch = files.slice(0, remaining);
    setUploading(true);
    setError('');
    try {
      try {
        await uploadEventPhotos(selected, batch);
        setUseLocal(false);
        await load();
      } catch {
        const extras: EventPhoto[] = [];
        for (const file of batch) {
          extras.push({
            id: `local-${crypto.randomUUID()}`,
            eventType: selected,
            fileName: file.name,
            caption: file.name,
            url: await fileToDataUrl(file),
            createdAt: new Date().toISOString(),
          });
        }
        const next = albumsForEvents(
          catalog.map((event) => {
            const current = albums.find((a) => a.eventType === event.eventType)?.photos ?? [];
            const photos = event.eventType === selected ? [...extras, ...current].slice(0, MAX_PHOTOS_PER_EVENT) : current;
            return { eventType: event.eventType, count: photos.length, photos };
          }),
          catalog,
        );
        writeLocalAlbums(next);
        setAlbums(next);
        setUseLocal(true);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not upload photos.');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  }

  async function handleDelete(id: string) {
    setError('');
    try {
      if (!useLocal && !id.startsWith('local-')) {
        await deleteEventPhoto(id);
        await load();
        return;
      }
      const next = albumsForEvents(
        albums.map((a) => ({
          ...a,
          photos: a.photos.filter((p) => p.id !== id),
          count: a.photos.filter((p) => p.id !== id).length,
        })),
        catalog,
      );
      writeLocalAlbums(next);
      setAlbums(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not delete photo.');
    }
  }

  function handleCreateEvent(e: React.FormEvent) {
    e.preventDefault();
    const name = newEventName.trim();
    if (!name) return;
    if (catalog.some((c) => c.eventType.toLowerCase() === name.toLowerCase())) {
      setError('That event already exists.');
      return;
    }
    const created: PhotoEventDef = {
      eventType: name,
      coverUrl: DEFAULT_COVER,
      blurb: `Up to ${MAX_PHOTOS_PER_EVENT} photos`,
    };
    const extra = [...readCustomEvents(), created];
    writeCustomEvents(extra);
    const nextCatalog = mergeCatalog(extra);
    setCatalog(nextCatalog);
    setAlbums(albumsForEvents([...albums, { eventType: name, count: 0, photos: [] }], nextCatalog));
    setNewEventName('');
    setShowForm(false);
    setError('');
    setSelected(name);
  }

  return (
    <>
      <PageHeader
        title={album ? `${album.eventType} photos` : 'Photos'}
        description={
          album
            ? `${album.count} of ${MAX_PHOTOS_PER_EVENT} photos. WhatsApp will send these when a customer asks about this event.`
            : 'Create an event in the header, then add up to 5 photos for it.'
        }
      />
      <ErrorBanner message={error} />

      {showForm && (
        <Card id="page-create-form" className="p-6 mb-6">
          <form onSubmit={handleCreateEvent} className="flex flex-col sm:flex-row gap-3">
            <input
              required
              placeholder="Event name (e.g. Engagement)"
              value={newEventName}
              onChange={(e) => setNewEventName(e.target.value)}
              className="flex-1 px-3 py-2.5 border border-[var(--border)] rounded-xl bg-[var(--card)] text-[var(--foreground)]"
            />
            <div className="flex gap-2">
              <Button type="submit">Save event</Button>
              <button
                type="button"
                onClick={() => {
                  setShowForm(false);
                  setNewEventName('');
                }}
                className="px-4 py-2.5 text-sm border border-[var(--border)] rounded-xl hover:bg-[var(--sidebar-hover)]"
              >
                Cancel
              </button>
            </div>
          </form>
        </Card>
      )}

      {album ? (
        <>
          <div className="flex flex-wrap items-center gap-3 mb-4">
            <button
              type="button"
              onClick={() => setSelected(null)}
              className="inline-flex items-center gap-2 text-sm text-[var(--muted)] hover:text-[var(--foreground)]"
            >
              <ArrowLeft size={16} />
              All events
            </button>
            <Button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading || remaining <= 0}
              className="ml-auto"
            >
              {uploading ? 'Uploading…' : remaining <= 0 ? 'Limit reached' : 'Add photos'}
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp,image/gif,.jpg,.jpeg,.png,.webp,.gif"
              multiple
              className="hidden"
              onChange={(e) => void addFiles(e.target.files)}
            />
          </div>

          {remaining > 0 && (
            <button
              type="button"
              disabled={uploading}
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragging(false);
                void addFiles(e.dataTransfer.files);
              }}
              className={`w-full mb-6 rounded-[var(--radius-xl)] border-2 border-dashed px-4 py-8 text-center transition-colors ${
                dragging
                  ? 'border-[var(--primary)] bg-[var(--primary-light)]'
                  : 'border-[var(--border)] bg-[var(--card)] hover:border-[var(--primary)]/50'
              }`}
            >
              <Upload size={22} className="mx-auto mb-2 text-[var(--muted)]" />
              <p className="text-sm font-medium text-[var(--foreground)]">
                Add up to {remaining} more {album.eventType.toLowerCase()} photo{remaining === 1 ? '' : 's'}
              </p>
              <p className="text-xs text-[var(--muted)] mt-1">Drop images here or click to choose (max {MAX_PHOTOS_PER_EVENT})</p>
            </button>
          )}

          {album.photos.length === 0 ? (
            <EmptyState message={`No ${album.eventType.toLowerCase()} photos yet. Add up to ${MAX_PHOTOS_PER_EVENT}.`} />
          ) : (
            <PhotoGrid photos={album.photos} eventType={album.eventType} onDelete={handleDelete} />
          )}
        </>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 grid-cards-equal">
          {eventCards.map((item) => (
            <button
              key={item.eventType}
              type="button"
              onClick={() => setSelected(item.eventType)}
              className="card-tile text-left"
            >
              <Card className="card-tile overflow-hidden hover:border-[var(--primary)]/40 transition-colors">
                <img
                  src={item.coverUrl}
                  alt={item.eventType}
                  className="w-full h-52 shrink-0 object-cover bg-[var(--sidebar-hover)]"
                />
                <div className="card-tile__body p-4">
                  <h3 className="text-sm font-medium text-[var(--foreground)] line-clamp-1">{item.eventType}</h3>
                  <p className="text-xs text-[var(--muted)] mt-1 line-clamp-2 min-h-[2.5rem] leading-relaxed">
                    {item.blurb}
                  </p>
                  <p className="text-xs text-[var(--muted)] mt-1 tabular-nums">
                    {item.count}/{MAX_PHOTOS_PER_EVENT} photos
                  </p>
                  <p className="card-tile__foot pt-2 text-xs text-[var(--primary)] font-medium inline-flex items-center gap-1">
                    <ImagePlus size={14} />
                    Open {item.eventType}
                  </p>
                </div>
              </Card>
            </button>
          ))}
        </div>
      )}
    </>
  );
}

function PhotoGrid({
  photos,
  eventType,
  onDelete,
}: {
  photos: EventPhoto[];
  eventType: string;
  onDelete: (id: string) => void;
}) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 grid-cards-equal">
      {photos.map((photo) => (
        <Card key={photo.id} className="card-tile overflow-hidden">
          <img
            src={photo.url}
            alt={photo.caption || eventType}
            className="w-full h-52 shrink-0 object-cover bg-[var(--sidebar-hover)]"
          />
          <div className="card-tile__body p-4 flex flex-row items-start justify-between gap-3 min-h-[4.5rem]">
            <p className="text-sm font-medium text-[var(--foreground)] line-clamp-2 min-w-0">
              {photo.caption || photo.fileName}
            </p>
            <button
              type="button"
              onClick={() => onDelete(photo.id)}
              className="text-xs text-red-600 hover:underline shrink-0"
            >
              Delete
            </button>
          </div>
        </Card>
      ))}
    </div>
  );
}
