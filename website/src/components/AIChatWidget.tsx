import { useEffect, useRef, useState } from 'react';
import { Bot, Loader2, Sparkles, X } from 'lucide-react';
import { askDashboardAssistant } from '../api/client';
import { AI_ASSISTANT_RULES, renderMarkdownish } from '../utils/aiAssistantRules';
import { BRAND_NAME_SHORT } from '../brand';

export function AIChatWidget() {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<{ role: 'user' | 'assistant'; text: string }[]>([]);
  const threadRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, loading]);

  async function runRule(rule: (typeof AI_ASSISTANT_RULES)[number]) {
    if (loading) return;

    setMessages((prev) => [...prev, { role: 'user', text: rule.query }]);
    setLoading(true);

    try {
      const { reply } = await askDashboardAssistant(rule.query, rule.id);
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
    <div className="ai-chat">
      {open && (
        <div className="ai-chat__panel" role="dialog" aria-label="AI Assistant chat">
          <header className="ai-chat__head">
            <div className="ai-chat__avatar ai-chat__avatar--brand">
              <Sparkles size={18} />
            </div>
            <div className="ai-chat__head-text">
              <p className="ai-chat__title">{BRAND_NAME_SHORT} AI</p>
              <p className="ai-chat__subtitle">Pick a quick question</p>
            </div>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="ai-chat__icon-btn"
              aria-label="Close chat"
            >
              <X size={18} />
            </button>
          </header>

          <div ref={threadRef} className="ai-chat__thread">
            {messages.length === 0 ? (
              <div className="ai-chat__empty">
                <div className="ai-chat__avatar ai-chat__avatar--soft">
                  <Bot size={26} />
                </div>
                <p className="ai-chat__empty-title">Hi! Ask about your events</p>
                <p className="ai-chat__empty-copy">
                  Use the questions below for live enquiry data.
                </p>
              </div>
            ) : (
              messages.map((msg, i) => (
                <div
                  key={i}
                  className={`ai-chat__row ${msg.role === 'user' ? 'ai-chat__row--user' : 'ai-chat__row--bot'}`}
                >
                  {msg.role === 'assistant' && (
                    <div className="ai-chat__avatar ai-chat__avatar--sm">
                      <Bot size={12} />
                    </div>
                  )}
                  <div className={`ai-chat__bubble ai-chat__bubble--${msg.role}`}>
                    {msg.role === 'assistant' ? renderMarkdownish(msg.text) : msg.text}
                  </div>
                </div>
              ))
            )}
            {loading && (
              <div className="ai-chat__loading">
                <Loader2 size={14} className="animate-spin" />
                Thinking…
              </div>
            )}
          </div>

          <footer className="ai-chat__footer">
            <p className="ai-chat__footer-label">Quick questions</p>
            <div className="ai-chat__chips">
              {AI_ASSISTANT_RULES.map((rule) => (
                <button
                  key={rule.id}
                  type="button"
                  onClick={() => void runRule(rule)}
                  disabled={loading}
                  className="ai-chat__chip"
                >
                  {rule.label}
                </button>
              ))}
            </div>
          </footer>
        </div>
      )}

      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={`ai-chat__fab ${open ? 'ai-chat__fab--open' : ''}`}
        aria-label={open ? 'Close AI chat' : 'Open AI chat'}
        title="AI Assistant"
      >
        {open ? <X size={22} /> : <Bot size={26} />}
      </button>
    </div>
  );
}
