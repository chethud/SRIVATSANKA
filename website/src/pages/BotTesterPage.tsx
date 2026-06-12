import { useCallback, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { MessageCircle, Plus, RefreshCw, Send, User } from 'lucide-react';
import { PageHeader } from '../components/Layout';
import { useAppData } from '../context/AppDataContext';
import {
  fetchChatConversations,
  fetchChatMessages,
  formatDateTime,
  formatPhoneDisplay,
  normalizePhoneInput,
  sendOwnerChatMessage,
  testBotMessage,
  resumeChatBot,
  type ChatConversation,
  type ChatMessage,
} from '../api/client';

type SendMode = 'customer' | 'owner';

function roleLabel(role: string) {
  if (role === 'customer') return 'Customer';
  if (role === 'owner') return 'You (team)';
  return 'Bot';
}

export default function BotTesterPage() {
  const { refresh, connected } = useAppData();
  const [searchParams, setSearchParams] = useSearchParams();
  const [conversations, setConversations] = useState<ChatConversation[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [selectedPhone, setSelectedPhone] = useState('');
  const [newPhone, setNewPhone] = useState('');
  const [input, setInput] = useState('');
  const [sendMode, setSendMode] = useState<SendMode>('owner');
  const [loadingList, setLoadingList] = useState(true);
  const [loadingThread, setLoadingThread] = useState(false);
  const [sending, setSending] = useState(false);
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
      setSendMode('owner');
      autoSelectedRef.current = true;
      return;
    }

    if (conversations.length > 0) {
      const first = conversations[0].phoneNumber;
      setSelectedPhone(first);
      setSearchParams({ phone: first }, { replace: true });
      setSendMode('owner');
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

  function selectConversation(phone: string, mode: SendMode = 'owner') {
    setSelectedPhone(phone);
    setSearchParams({ phone });
    setSendMode(mode);
    setError('');
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

  async function resumeBot() {
    if (!selectedPhone) return;
    setError('');
    try {
      await resumeChatBot(selectedPhone);
      await loadConversations();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not resume bot.');
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
      } else {
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

  return (
    <>
      <PageHeader
        title="WhatsApp Chat"
        description="Live customer conversations by phone — open a thread and reply directly to their WhatsApp"
      />

      {!connected && (
        <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 mb-4">
          API offline — start the backend on Render or locally, then sign in again.
        </p>
      )}

      <div className="text-sm text-[var(--muted)] mb-4 space-y-1">
        <p>
          When a customer messages your Meta business number, their chat appears here with their phone number.
          Click the conversation, type a message, and choose <strong>Send to customer</strong> — they receive it on WhatsApp.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[320px_minmax(0,1fr)] gap-4 h-[min(720px,calc(100vh-280px))]">
        <aside className="bg-[var(--card)] border border-[var(--border)] rounded-xl flex flex-col overflow-hidden">
          <div className="p-4 border-b border-[var(--border)]">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-[var(--order-accent)]">
                Conversations ({conversations.length})
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
                className="form-input flex-1 px-3 py-2 rounded-lg text-sm"
              />
              <button
                type="button"
                onClick={startNewChat}
                className="px-3 py-2 rounded-lg bg-[var(--primary)] text-white hover:bg-[var(--primary-hover)]"
                title="Open chat by phone"
              >
                <Plus size={18} />
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto">
            {loadingList && conversations.length === 0 ? (
              <p className="text-sm text-[var(--muted)] p-4">Loading conversations…</p>
            ) : conversations.length === 0 ? (
              <p className="text-sm text-[var(--muted)] p-4">
                No chats yet. Send <strong>Hi</strong> from a customer phone to your Meta business number — it will show up here.
              </p>
            ) : (
              conversations.map((c) => {
                const activeRow = c.phoneNumber === selectedPhone;
                return (
                  <button
                    key={c.phoneNumber}
                    type="button"
                    onClick={() => selectConversation(c.phoneNumber, 'owner')}
                    className={`w-full text-left px-4 py-3 border-b border-[var(--border)] transition-colors ${
                      activeRow ? 'bg-[var(--primary-light)]' : 'hover:bg-[var(--sidebar-hover)]'
                    }`}
                  >
                    <div className="flex items-start gap-3">
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
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </aside>

        <section className="bg-[var(--card)] border border-[var(--border)] rounded-xl flex flex-col overflow-hidden">
          {!selectedPhone ? (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-8 text-[var(--muted)]">
              <MessageCircle size={40} className="mb-3 opacity-40" />
              <p className="font-medium text-[var(--foreground)]">Select a conversation</p>
              <p className="text-sm mt-1">Pick a phone number on the left to view history and reply.</p>
            </div>
          ) : (
            <>
              <div className="px-4 py-3 border-b border-[var(--border)] bg-[var(--background)] flex items-center justify-between gap-3">
                <div>
                  <p className="font-semibold">{formatPhoneDisplay(selectedPhone)}</p>
                  <p className="text-xs text-[var(--muted)]">
                    {active?.customerName ? `${active.customerName} · ` : ''}
                    WhatsApp thread
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {active?.botPaused && (
                    <button
                      type="button"
                      onClick={() => void resumeBot()}
                      className="text-xs px-2.5 py-1 rounded-full border border-[var(--border)] hover:bg-[var(--sidebar-hover)]"
                    >
                      Resume auto-reply
                    </button>
                  )}
                  <span className="text-xs px-2 py-1 rounded-full bg-[var(--primary-light)] text-[var(--primary)] font-medium">
                    {messages.length} messages
                  </span>
                </div>
              </div>

              {active?.botPaused && (
                <p className="text-xs text-amber-800 bg-amber-50 border-b border-amber-200 px-4 py-2">
                  Auto-reply is off for this customer — you are handling the chat. The bot will not reply until you click{' '}
                  <strong>Resume auto-reply</strong>.
                </p>
              )}

              <div ref={threadRef} className="flex-1 overflow-y-auto p-4 space-y-3">
                {loadingThread && messages.length === 0 ? (
                  <p className="text-sm text-[var(--muted)] text-center mt-10">Loading messages…</p>
                ) : messages.length === 0 ? (
                  <p className="text-sm text-[var(--muted)] text-center mt-10">
                    No messages stored yet for this number. If they messaged on WhatsApp, wait a few seconds or refresh.
                  </p>
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
                                : 'bg-[var(--background)] border border-[var(--border)]'
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

              <div className="border-t border-[var(--border)] p-4 space-y-3">
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => setSendMode('owner')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold ${
                      sendMode === 'owner'
                        ? 'bg-[var(--primary)] text-white'
                        : 'bg-[var(--background)] border border-[var(--border)]'
                    }`}
                  >
                    Send to customer (WhatsApp)
                  </button>
                  <button
                    type="button"
                    onClick={() => setSendMode('customer')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold ${
                      sendMode === 'customer'
                        ? 'bg-[var(--primary)] text-white'
                        : 'bg-[var(--background)] border border-[var(--border)]'
                    }`}
                  >
                    Simulate customer (bot test)
                  </button>
                </div>
                {sendMode === 'owner' && (
                  <p className="text-xs text-[var(--muted)]">
                    Your message goes to {formatPhoneDisplay(selectedPhone)} on WhatsApp. Auto-reply pauses while you handle this chat.
                  </p>
                )}
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    void sendMessage(input);
                  }}
                  className="flex gap-3"
                >
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder={
                      sendMode === 'owner'
                        ? 'Type your reply — customer receives this on WhatsApp…'
                        : 'Type as customer (e.g. Hi)…'
                    }
                    disabled={sending}
                    className="form-input flex-1 px-4 py-2 rounded-lg outline-none focus:border-[var(--primary)] disabled:opacity-50"
                  />
                  <button
                    type="submit"
                    disabled={sending || !input.trim()}
                    className="px-4 py-2 bg-[var(--primary)] text-white rounded-lg hover:bg-[var(--primary-hover)] disabled:opacity-50"
                  >
                    <Send size={18} />
                  </button>
                </form>
                {error && <p className="text-sm text-red-600">{error}</p>}
              </div>
            </>
          )}
        </section>
      </div>
    </>
  );
}
