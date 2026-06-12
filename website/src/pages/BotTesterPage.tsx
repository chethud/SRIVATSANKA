import { useCallback, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { MessageCircle, Plus, Send, User } from 'lucide-react';
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
  type ChatConversation,
  type ChatMessage,
} from '../api/client';

type SendMode = 'customer' | 'owner';

function roleLabel(role: string) {
  if (role === 'customer') return 'Customer';
  if (role === 'owner') return 'You';
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
  const [sendMode, setSendMode] = useState<SendMode>('customer');
  const [loadingList, setLoadingList] = useState(true);
  const [loadingThread, setLoadingThread] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const threadRef = useRef<HTMLDivElement>(null);

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
    const id = setInterval(() => void loadConversations(), 8000);
    return () => clearInterval(id);
  }, [loadConversations]);

  useEffect(() => {
    const fromUrl = searchParams.get('phone') || '';
    if (fromUrl && fromUrl !== selectedPhone) {
      setSelectedPhone(fromUrl);
    }
  }, [searchParams, selectedPhone]);

  useEffect(() => {
    if (!selectedPhone) return;
    void loadMessages(selectedPhone);
    const id = setInterval(() => void loadMessages(selectedPhone), 4000);
    return () => clearInterval(id);
  }, [selectedPhone, loadMessages]);

  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, loadingThread]);

  function selectConversation(phone: string) {
    setSelectedPhone(phone);
    setSearchParams(phone ? { phone } : {});
    setSendMode('customer');
  }

  function startNewChat() {
    const phone = normalizePhoneInput(newPhone);
    if (phone.length < 10) {
      setError('Enter a valid phone number with country code (e.g. 917899410254).');
      return;
    }
    setError('');
    selectConversation(phone);
    setNewPhone('');
  }

  async function sendMessage(text: string) {
    if (!text.trim() || !selectedPhone || sending) return;
    setSending(true);
    setError('');
    try {
      if (sendMode === 'owner') {
        await sendOwnerChatMessage(selectedPhone, text.trim());
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
        title="WhatsApp Chat & Bot Tester"
        description="View every customer conversation by phone, simulate the bot, or reply directly from the dashboard"
      />

      {!connected && (
        <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 mb-4">
          API offline — start the backend locally or check Render, then sign in again.
        </p>
      )}

      <div className="text-sm text-[var(--muted)] mb-4 space-y-1">
        <p>
          <strong>Test here:</strong> Sidebar → <strong>WhatsApp Chat</strong> (this page) at{' '}
          <code className="text-xs bg-[var(--background)] px-1.5 py-0.5 rounded">/bot-tester</code>
        </p>
        <p>
          <strong>Live WhatsApp:</strong> Message your Meta business/test number from a real phone — chats appear here automatically.
        </p>
        <p>
          Bot flow: Hi → name → event type → <strong>ok</strong> → details → meals. Customer mode simulates the bot; Team reply sends a real WhatsApp message.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[320px_minmax(0,1fr)] gap-4 h-[min(720px,calc(100vh-280px))]">
        <aside className="bg-[var(--card)] border border-[var(--border)] rounded-xl flex flex-col overflow-hidden">
          <div className="p-4 border-b border-[var(--border)]">
            <p className="text-xs font-semibold uppercase tracking-wide text-[var(--order-accent)] mb-2">
              Conversations
            </p>
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
                title="Open chat"
              >
                <Plus size={18} />
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto">
            {loadingList && conversations.length === 0 ? (
              <p className="text-sm text-[var(--muted)] p-4">Loading…</p>
            ) : conversations.length === 0 ? (
              <p className="text-sm text-[var(--muted)] p-4">
                No chats yet. Start a new number above or send Hi from Bot Tester / WhatsApp.
              </p>
            ) : (
              conversations.map((c) => {
                const activeRow = c.phoneNumber === selectedPhone;
                return (
                  <button
                    key={c.phoneNumber}
                    type="button"
                    onClick={() => selectConversation(c.phoneNumber)}
                    className={`w-full text-left px-4 py-3 border-b border-[var(--border)] transition-colors ${
                      activeRow ? 'bg-[var(--primary-light)]' : 'hover:bg-[var(--sidebar-hover)]'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <div className="w-9 h-9 rounded-full bg-[var(--background)] border border-[var(--border)] flex items-center justify-center shrink-0">
                        <User size={16} className="text-[var(--muted)]" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="font-semibold text-sm truncate">
                          {c.customerName || formatPhoneDisplay(c.phoneNumber)}
                        </p>
                        <p className="text-xs text-[var(--muted)]">{formatPhoneDisplay(c.phoneNumber)}</p>
                        <p className="text-xs text-[var(--muted)] mt-1 truncate">
                          {roleLabel(c.lastRole)}: {c.lastMessage}
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
              <div className="px-4 py-3 border-b border-[var(--border)] bg-[var(--background)]">
                <p className="font-semibold">{active?.customerName || 'Customer'}</p>
                <p className="text-xs text-[var(--muted)]">{formatPhoneDisplay(selectedPhone)}</p>
              </div>

              <div ref={threadRef} className="flex-1 overflow-y-auto p-4 space-y-3">
                {loadingThread && messages.length === 0 ? (
                  <p className="text-sm text-[var(--muted)] text-center mt-10">Loading messages…</p>
                ) : messages.length === 0 ? (
                  <p className="text-sm text-[var(--muted)] text-center mt-10">
                    No messages yet. Send Hi as the customer to start the bot flow.
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
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setSendMode('customer')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold ${
                      sendMode === 'customer'
                        ? 'bg-[var(--primary)] text-white'
                        : 'bg-[var(--background)] border border-[var(--border)]'
                    }`}
                  >
                    As customer (bot test)
                  </button>
                  <button
                    type="button"
                    onClick={() => setSendMode('owner')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold ${
                      sendMode === 'owner'
                        ? 'bg-[var(--primary)] text-white'
                        : 'bg-[var(--background)] border border-[var(--border)]'
                    }`}
                  >
                    Team reply (WhatsApp)
                  </button>
                </div>
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
                        ? 'Type your reply to the customer…'
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
