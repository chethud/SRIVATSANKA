import { useEffect, useRef, useState } from 'react';
import { Bot, Loader2, Sparkles, X } from 'lucide-react';
import { askDashboardAssistant } from '../api/client';
import { AI_ASSISTANT_RULES, renderMarkdownish } from '../utils/aiAssistantRules';

export function AIChatWidget() {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<{ role: 'user' | 'assistant'; text: string }[]>([]);
  const threadRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, loading]);

  async function runRule(query: string) {
    if (loading) return;

    setMessages((prev) => [...prev, { role: 'user', text: query }]);
    setLoading(true);

    try {
      const { reply } = await askDashboardAssistant(query);
      setMessages((prev) => [...prev, { role: 'assistant', text: reply }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: 'Could not reach the API. Check that the backend is running.',
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      {open && (
        <div
          className="fixed bottom-24 right-4 md:right-6 z-50 flex flex-col w-[min(calc(100vw-2rem),400px)] h-[min(calc(100vh-8rem),560px)] rounded-2xl border border-[var(--border)] bg-[var(--card)] shadow-[0_12px_48px_rgba(0,0,0,0.18)] overflow-hidden"
          role="dialog"
          aria-label="AI Assistant chat"
        >
          <div className="flex items-center gap-3 px-4 py-3 border-b border-[var(--border)] bg-gradient-to-r from-[var(--primary)] to-[var(--accent)] text-white shrink-0">
            <div className="w-10 h-10 rounded-full bg-white/20 backdrop-blur flex items-center justify-center ring-2 ring-white/30">
              <Sparkles size={20} />
            </div>
            <div className="min-w-0 flex-1">
              <p className="font-semibold text-sm">SRIVATSANKA EVENTS AI</p>
              <p className="text-xs text-white/80">Choose a question below</p>
            </div>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="p-2 rounded-full hover:bg-white/15 transition-colors"
              aria-label="Close chat"
            >
              <X size={18} />
            </button>
          </div>

          <div ref={threadRef} className="flex-1 overflow-y-auto p-4 space-y-3 bg-[var(--background)]">
            {messages.length === 0 ? (
              <div className="text-center pt-8 px-2">
                <div className="w-14 h-14 mx-auto mb-3 rounded-full bg-[var(--primary-light)] flex items-center justify-center">
                  <Bot size={28} className="text-[var(--primary)]" />
                </div>
                <p className="text-sm font-medium text-[var(--foreground)]">Hi! Pick a question</p>
                <p className="text-xs text-[var(--muted)] mt-1">
                  Tap one of the options below to see live enquiry data.
                </p>
              </div>
            ) : (
              messages.map((msg, i) => (
                <div
                  key={i}
                  className={`flex gap-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {msg.role === 'assistant' && (
                    <div className="w-7 h-7 rounded-full bg-[var(--primary)] flex items-center justify-center shrink-0 mt-1">
                      <Bot size={14} className="text-white" />
                    </div>
                  )}
                  <div
                    className={`max-w-[85%] px-3 py-2.5 rounded-2xl text-sm leading-relaxed ${
                      msg.role === 'user'
                        ? 'bg-[var(--primary)] text-white rounded-br-md'
                        : 'bg-[var(--card)] border border-[var(--border)] text-[var(--foreground)] rounded-bl-md'
                    }`}
                  >
                    {msg.role === 'assistant' ? renderMarkdownish(msg.text) : msg.text}
                  </div>
                </div>
              ))
            )}
            {loading && (
              <div className="flex items-center gap-2 text-xs text-[var(--muted)] pl-9">
                <Loader2 size={14} className="animate-spin" />
                Thinking…
              </div>
            )}
          </div>

          <div className="border-t border-[var(--border)] p-3 bg-[var(--card)] shrink-0">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)] mb-2 px-1">
              Quick questions
            </p>
            <div className="flex flex-wrap gap-2">
              {AI_ASSISTANT_RULES.map((rule) => (
                <button
                  key={rule.id}
                  type="button"
                  onClick={() => void runRule(rule.query)}
                  disabled={loading}
                  className="px-3 py-1.5 text-xs rounded-full border border-[var(--border)] bg-[var(--background)] hover:border-[var(--primary)] hover:bg-[var(--primary-light)] transition-colors disabled:opacity-50"
                >
                  {rule.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={`fixed bottom-5 right-4 md:right-6 z-50 w-14 h-14 rounded-full flex items-center justify-center shadow-[0_8px_32px_rgba(0,0,0,0.2)] transition-all duration-300 hover:scale-105 active:scale-95 ${
          open
            ? 'bg-[var(--card)] border-2 border-[var(--border)] text-[var(--foreground)]'
            : 'bg-gradient-to-br from-[var(--primary)] to-[var(--accent)] text-white ring-4 ring-[var(--primary)]/25'
        }`}
        aria-label={open ? 'Close AI chat' : 'Open AI chat'}
        title="AI Assistant"
      >
        {open ? <X size={22} /> : <Bot size={26} />}
      </button>
    </>
  );
}
