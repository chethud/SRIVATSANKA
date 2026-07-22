import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Plus, RefreshCw, Send, Trash2, User, X } from 'lucide-react';
import { useAppData } from '../context/AppDataContext';
import { WhatsAppIcon } from '../components/WhatsAppIcon';
import {
  deleteChatConversation,
  fetchChatConversations,
  fetchChatMessages,
  formatDateTime,
  formatPhoneDisplay,
  normalizePhoneInput,
  sendOwnerChatMessage,
  testBotMessage,
  pauseChatBot,
  resumeChatBot,
  type ChatConversation,
  type ChatMessage,
} from '../api/client';

/** idle = bot auto-replies; owner = manual reply; customer = simulate inbound */
type SendMode = 'idle' | 'customer' | 'owner';

function roleLabel(role: string) {
  if (role === 'customer') return 'Customer';
  if (role === 'owner') return 'You (team)';
  return 'Bot';
}

function profileInitials(name: string | null | undefined, phone: string) {
  const trimmed = name?.trim();
  if (trimmed) {
    const parts = trimmed.split(/\s+/).filter(Boolean);
    const letters = `${parts[0]?.[0] ?? ''}${parts[1]?.[0] ?? ''}`.toUpperCase();
    if (letters) return letters;
  }
  const digits = normalizePhoneInput(phone);
  return (digits.slice(-2) || '?').toUpperCase();
}

function whatsappDpUrl(name: string | null | undefined, phone: string) {
  const label = name?.trim() || formatPhoneDisplay(phone) || phone;
  return `https://ui-avatars.com/api/?name=${encodeURIComponent(label)}&background=25D366&color=ffffff&size=512&bold=true&format=png`;
}

export default function BotTesterPage() {
  const { refresh, connected } = useAppData();
  const [searchParams, setSearchParams] = useSearchParams();
  const [conversations, setConversations] = useState<ChatConversation[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [selectedPhone, setSelectedPhone] = useState('');
  const [newPhone, setNewPhone] = useState('');
  const [input, setInput] = useState('');
  const [sendMode, setSendMode] = useState<SendMode>('idle');
  const [loadingList, setLoadingList] = useState(true);
  const [loadingThread, setLoadingThread] = useState(false);
  const [sending, setSending] = useState(false);
  const [pausing, setPausing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [dpFailed, setDpFailed] = useState(false);
  const [error, setError] = useState('');
  const threadRef = useRef<HTMLDivElement>(null);
  const autoSelectedRef = useRef(false);

  const loadConversations = useCallback(async () => {
    try {
      const rows = await fetchChatConversations();
      setConversations(rows);
      setError('');
    } catch {
      setError('Could not load conversations. Check that the API is running and you are signed in.');
    } finally {
      setLoadingList(false);
    }
  }, []);

  const loadMessages = useCallback(async (phone: string) => {
    if (!phone) {
      setMessages([]);
      return;
    }
    setLoadingThread(true);
    try {
      const rows = await fetchChatMessages(phone);
      setMessages(rows);
      setError('');
    } catch {
      setError('Could not load chat history for this number.');
    } finally {
      setLoadingThread(false);
    }
  }, []);

  useEffect(() => {
    void loadConversations();
    const id = setInterval(() => void loadConversations(), 5000);
    return () => clearInterval(id);
  }, [loadConversations]);

  useEffect(() => {
    if (loadingList || autoSelectedRef.current) return;

    const fromUrl = normalizePhoneInput(searchParams.get('phone') || '');
    if (fromUrl) {
      setSelectedPhone(fromUrl);
      setSendMode('idle');
      autoSelectedRef.current = true;
      return;
    }

    if (conversations.length > 0) {
      const first = conversations[0].phoneNumber;
      setSelectedPhone(first);
      setSearchParams({ phone: first }, { replace: true });
      setSendMode('idle');
      autoSelectedRef.current = true;
    }
  }, [loadingList, conversations, searchParams, setSearchParams]);

  useEffect(() => {
    if (!selectedPhone) return;
    void loadMessages(selectedPhone);
    const id = setInterval(() => void loadMessages(selectedPhone), 3000);
    return () => clearInterval(id);
  }, [selectedPhone, loadMessages]);

  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, loadingThread]);

  function selectConversation(phone: string, mode?: SendMode) {
    const row = conversations.find((c) => c.phoneNumber === phone);
    const nextMode = mode ?? (row?.botPaused ? 'owner' : 'idle');
    setSelectedPhone(phone);
    setSearchParams({ phone });
    setSendMode(nextMode);
    setInput('');
    setError('');
    setProfileOpen(false);
    setDpFailed(false);
  }

  function startNewChat() {
    const phone = normalizePhoneInput(newPhone);
    if (phone.length < 10) {
      setError('Enter a valid phone number with country code (e.g. 917899410254).');
      return;
    }
    setError('');
    selectConversation(phone, 'customer');
    setNewPhone('');
  }

  function patchBotPaused(phone: string, paused: boolean) {
    setConversations((prev) =>
      prev.map((c) => (c.phoneNumber === phone ? { ...c, botPaused: paused } : c)),
    );
  }

  async function startReply() {
    if (!selectedPhone || pausing) return;
    setPausing(true);
    setError('');
    try {
      await pauseChatBot(selectedPhone);
      patchBotPaused(selectedPhone, true);
      setSendMode('owner');
      await loadConversations();
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not take over this chat.');
    } finally {
      setPausing(false);
    }
  }

  async function resumeBot() {
    if (!selectedPhone) return;
    setError('');
    try {
      await resumeChatBot(selectedPhone);
      patchBotPaused(selectedPhone, false);
      setSendMode('idle');
      setInput('');
      await loadConversations();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not resume bot.');
    }
  }

  async function deleteChat() {
    if (!selectedPhone || deleting) return;
    const row = conversations.find((c) => c.phoneNumber === selectedPhone);
    const label = row?.customerName
      ? `${row.customerName} (${formatPhoneDisplay(selectedPhone)})`
      : formatPhoneDisplay(selectedPhone);
    if (!window.confirm(`Delete chat with ${label}? This removes the message history from the dashboard.`)) {
      return;
    }
    setDeleting(true);
    setError('');
    try {
      await deleteChatConversation(selectedPhone);
      setMessages([]);
      setSelectedPhone('');
      setSearchParams({}, { replace: true });
      autoSelectedRef.current = false;
      await loadConversations();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not delete chat.');
    } finally {
      setDeleting(false);
    }
  }

  async function sendMessage(text: string) {
    if (!text.trim() || !selectedPhone || sending) return;
    setSending(true);
    setError('');
    try {
      if (sendMode === 'owner') {
        await sendOwnerChatMessage(selectedPhone, text.trim());
        setSendMode('owner');
        refresh();
      } else if (sendMode === 'customer') {
        const res = await testBotMessage(selectedPhone, text.trim());
        if (res.enquiry_saved) refresh();
      }
      setInput('');
      await loadMessages(selectedPhone);
      await loadConversations();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not send message.');
    } finally {
      setSending(false);
    }
  }

  const active = conversations.find((c) => c.phoneNumber === selectedPhone);
  const botPaused = Boolean(active?.botPaused);
  const ownerReplying = botPaused || sendMode === 'owner';
  const profileName = active?.customerName ?? null;
  const profileDp = selectedPhone ? whatsappDpUrl(profileName, selectedPhone) : '';
  const profileLetters = selectedPhone ? profileInitials(profileName, selectedPhone) : '?';

  useEffect(() => {
    if (!selectedPhone || !botPaused) return;
    setSendMode((mode) => (mode === 'customer' ? mode : 'owner'));
  }, [selectedPhone, botPaused]);

  return (
    <div className="wa-chats">
      {profileOpen && selectedPhone && (
        <div
          className="wa-dp-overlay"
          role="dialog"
          aria-modal="true"
          aria-label="WhatsApp profile photo"
          onClick={() => setProfileOpen(false)}
        >
          <button
            type="button"
            className="wa-dp-close"
            onClick={() => setProfileOpen(false)}
            aria-label="Close profile photo"
          >
            <X size={22} />
          </button>
          <div className="wa-dp-body" onClick={(e) => e.stopPropagation()}>
            {!dpFailed ? (
              <img
                src={profileDp}
                alt={profileName || formatPhoneDisplay(selectedPhone)}
                className="wa-dp-photo"
                onError={() => setDpFailed(true)}
              />
            ) : (
              <div className="wa-dp-fallback">{profileLetters}</div>
            )}
            <p className="wa-dp-name">{profileName || formatPhoneDisplay(selectedPhone)}</p>
            {profileName && (
              <p className="wa-dp-phone">{formatPhoneDisplay(selectedPhone)}</p>
            )}
            <div className="wa-dp-actions">
              <a
                href={`https://wa.me/${normalizePhoneInput(selectedPhone)}`}
                target="_blank"
                rel="noreferrer"
                className="wa-dp-action"
              >
                Open in WhatsApp
              </a>
              {active?.enquiryId && (
                <Link
                  to={`/enquiries?id=${encodeURIComponent(active.enquiryId)}`}
                  className="wa-dp-action wa-dp-action--muted"
                  onClick={() => setProfileOpen(false)}
                >
                  View enquiry
                </Link>
              )}
            </div>
          </div>
        </div>
      )}

      <header className="wa-chats__header">
        <WhatsAppIcon size={22} title="WhatsApp" />
        <h1 className="wa-chats__title">WhatsApp Chats</h1>
        {!connected && (
          <p className="wa-chats__offline">API offline — sign in again after the backend is running.</p>
        )}
      </header>

      {error && !selectedPhone && (
        <p className="wa-chats__banner">{error}</p>
      )}

      <div className="wa-chats__body">
        <aside className="wa-chats__list">
          <div className="wa-chats__list-toolbar">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-semibold text-[var(--muted)]">
                {conversations.length} chat{conversations.length === 1 ? '' : 's'}
              </p>
              <button
                type="button"
                onClick={() => void loadConversations()}
                className="p-1.5 rounded-lg hover:bg-[var(--sidebar-hover)] text-[var(--muted)]"
                title="Refresh list"
              >
                <RefreshCw size={14} />
              </button>
            </div>
            <div className="flex gap-2">
              <input
                type="tel"
                value={newPhone}
                onChange={(e) => setNewPhone(e.target.value)}
                placeholder="917899410254"
                className="form-input flex-1 min-w-0 px-3 py-2 rounded-lg text-sm"
              />
              <button
                type="button"
                onClick={startNewChat}
                className="px-3 py-2 rounded-lg bg-[var(--primary)] text-white hover:bg-[var(--primary-hover)] shrink-0"
                title="Open chat by phone"
              >
                <Plus size={18} />
              </button>
            </div>
          </div>

          <div className="wa-chats__list-scroll">
            {loadingList && conversations.length === 0 ? (
              <p className="text-sm text-[var(--muted)] p-4">Loading conversations…</p>
            ) : conversations.length === 0 ? (
              <p className="text-sm text-[var(--muted)] p-4">No chats yet. Enter a phone number above to start.</p>
            ) : (
              conversations.map((c) => {
                const activeRow = c.phoneNumber === selectedPhone;
                return (
                  <button
                    key={c.phoneNumber}
                    type="button"
                    onClick={() => selectConversation(c.phoneNumber)}
                    className={`wa-chats__row ${activeRow ? 'wa-chats__row--active' : ''}`}
                  >
                    <div className="w-9 h-9 rounded-full bg-[var(--background)] border border-[var(--border)] flex items-center justify-center shrink-0">
                      <User size={16} className="text-[var(--muted)]" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold text-sm truncate">{formatPhoneDisplay(c.phoneNumber)}</p>
                      {c.customerName && (
                        <p className="text-xs text-[var(--foreground)] truncate">{c.customerName}</p>
                      )}
                      <p className="text-xs text-[var(--muted)] mt-1 truncate">
                        {roleLabel(c.lastRole)}: {c.lastMessage}
                      </p>
                      <p className="text-[10px] text-[var(--muted)] mt-0.5">
                        {formatDateTime(c.lastAt)} · {c.messageCount} msgs
                        {c.botPaused ? ' · You are replying' : ''}
                      </p>
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </aside>

        <section className="wa-chats__thread">
          {!selectedPhone ? (
            <div className="wa-chats__empty">
              <WhatsAppIcon size={48} className="opacity-40 mb-3" />
              <p className="text-sm text-[var(--muted)]">Select a chat or open a number to start</p>
            </div>
          ) : (
            <>
              <div className="wa-chats__thread-head">
                <button
                  type="button"
                  className="wa-chats__thread-profile"
                  onClick={() => setProfileOpen(true)}
                  title="View profile photo"
                >
                  {!dpFailed ? (
                    <img
                      src={profileDp}
                      alt=""
                      className="wa-chats__avatar"
                      onError={() => setDpFailed(true)}
                    />
                  ) : (
                    <span className="wa-chats__avatar wa-chats__avatar--fallback">{profileLetters}</span>
                  )}
                  <div className="min-w-0 text-left">
                    <p className="font-semibold truncate">{formatPhoneDisplay(selectedPhone)}</p>
                    {active?.customerName && (
                      <p className="text-xs text-[var(--muted)] truncate">{active.customerName}</p>
                    )}
                  </div>
                </button>
                <div className="flex items-center gap-2 shrink-0">
                  {active?.botPaused && (
                    <button
                      type="button"
                      onClick={() => void resumeBot()}
                      className="text-xs px-2.5 py-1 rounded-full border border-[var(--border)] hover:bg-[var(--sidebar-hover)]"
                    >
                      Resume bot
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => void deleteChat()}
                    disabled={deleting}
                    className="inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border border-[var(--border)] text-[var(--danger)] hover:bg-[var(--danger-bg)] disabled:opacity-50"
                    title="Delete chat"
                  >
                    <Trash2 size={14} />
                    {deleting ? 'Deleting…' : 'Delete'}
                  </button>
                </div>
              </div>

              <div ref={threadRef} className="wa-chats__messages">
                {loadingThread && messages.length === 0 ? (
                  <p className="text-sm text-[var(--muted)] text-center mt-10">Loading messages…</p>
                ) : messages.length === 0 ? (
                  <p className="text-sm text-[var(--muted)] text-center mt-10">No messages yet.</p>
                ) : (
                  messages.map((msg) => {
                    const isCustomer = msg.role === 'customer';
                    const isOwner = msg.role === 'owner';
                    return (
                      <div
                        key={msg.id}
                        className={`max-w-[85%] ${isCustomer ? 'ml-auto' : ''}`}
                      >
                        <p className="text-[10px] uppercase tracking-wide text-[var(--muted)] mb-1">
                          {roleLabel(msg.role)} · {formatDateTime(msg.createdAt)}
                        </p>
                        <div
                          className={`p-3 rounded-xl text-sm whitespace-pre-wrap ${
                            isCustomer
                              ? 'bg-[#dcf8c6] text-[#111]'
                              : isOwner
                                ? 'bg-[var(--primary-light)] border border-[var(--primary)]/20 text-[var(--foreground)]'
                                : 'bg-[var(--card)] border border-[var(--border)]'
                          }`}
                        >
                          {msg.body}
                        </div>
                        {msg.media && msg.media.length > 0 && (
                          <div className="mt-2 grid grid-cols-1 gap-2">
                            {msg.media.map((m, j) => (
                              <figure key={j} className="rounded-lg overflow-hidden border border-[var(--border)]">
                                <img
                                  src={m.url}
                                  alt={m.caption || 'Photo'}
                                  className="w-full max-h-48 object-cover"
                                />
                                {m.caption && (
                                  <figcaption className="text-xs p-2 text-[var(--muted)]">{m.caption}</figcaption>
                                )}
                              </figure>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })
                )}
              </div>

              <div className="wa-chats__composer">
                {error && <p className="text-sm text-red-600 mb-2">{error}</p>}
                {!ownerReplying && sendMode !== 'customer' ? (
                  <div className="space-y-3">
                    <p className="text-sm text-[var(--muted)]">
                      Bot is auto-replying on WhatsApp. Click Reply to take over and message manually.
                    </p>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => void startReply()}
                        disabled={pausing || !connected}
                        className="px-4 py-2.5 rounded-xl text-sm font-semibold bg-[var(--primary)] text-white hover:bg-[var(--primary-hover)] disabled:opacity-50"
                      >
                        {pausing ? 'Taking over…' : 'Reply'}
                      </button>
                      <button
                        type="button"
                        onClick={() => setSendMode('customer')}
                        className="px-4 py-2.5 rounded-xl text-sm font-semibold bg-[var(--background)] border border-[var(--border)] hover:bg-[var(--sidebar-hover)]"
                      >
                        Bot test
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="flex flex-wrap items-center gap-2 mb-2">
                      {ownerReplying ? (
                        <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-[var(--primary-light)] text-[var(--primary)]">
                          You are replying — bot paused
                        </span>
                      ) : (
                        <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-[var(--background)] border border-[var(--border)]">
                          Bot test mode
                        </span>
                      )}
                      {sendMode === 'customer' && !ownerReplying && (
                        <button
                          type="button"
                          onClick={() => setSendMode('idle')}
                          className="text-xs px-2.5 py-1 rounded-full border border-[var(--border)] hover:bg-[var(--sidebar-hover)]"
                        >
                          Back
                        </button>
                      )}
                      {ownerReplying && (
                        <button
                          type="button"
                          onClick={() => void resumeBot()}
                          className="text-xs px-2.5 py-1 rounded-full border border-[var(--border)] hover:bg-[var(--sidebar-hover)]"
                        >
                          Resume bot
                        </button>
                      )}
                    </div>
                    <form
                      onSubmit={(e) => {
                        e.preventDefault();
                        void sendMessage(input);
                      }}
                      className="flex gap-2"
                    >
                      <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder={ownerReplying ? 'Type your WhatsApp reply…' : 'Simulate customer…'}
                        disabled={sending}
                        className="form-input flex-1 min-w-0 px-4 py-2.5 rounded-xl outline-none focus:border-[var(--primary)] disabled:opacity-50"
                      />
                      <button
                        type="submit"
                        disabled={sending || !input.trim()}
                        className="px-4 py-2 bg-[var(--primary)] text-white rounded-lg hover:bg-[var(--primary-hover)] disabled:opacity-50 shrink-0"
                      >
                        <Send size={18} />
                      </button>
                    </form>
                  </>
                )}
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
