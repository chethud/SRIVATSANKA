import { useState } from 'react';
import { Loader2 } from 'lucide-react';
import { PageHeader } from '../components/Layout';
import { askDashboardAssistant } from '../api/client';
import { AI_ASSISTANT_RULES, renderMarkdownish } from '../utils/aiAssistantRules';

export default function AIAssistantPage() {
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<{ role: 'user' | 'assistant'; text: string }[]>([]);

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
          text: 'Could not reach the API. Make sure FastAPI is running on port 8001.',
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <PageHeader
        title="AI Assistant"
        description="Choose a question to see enquiries, events, and business stats"
      />
      <div className="bg-[var(--card)] border border-[var(--border)] rounded-xl flex flex-col h-[500px] shadow-sm">
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 ? (
            <p className="text-[var(--muted)] text-center mt-20">
              Pick a question below to see live enquiry data
            </p>
          ) : (
            messages.map((msg, i) => (
              <div
                key={i}
                className={`max-w-[85%] p-4 rounded-xl text-sm leading-relaxed ${
                  msg.role === 'user'
                    ? 'ml-auto bg-[var(--primary)] text-white'
                    : 'bg-[var(--background)] border border-[var(--border)] text-[var(--foreground)]'
                }`}
              >
                {msg.role === 'assistant' ? renderMarkdownish(msg.text) : msg.text}
              </div>
            ))
          )}
          {loading && (
            <div className="flex items-center gap-2 text-sm text-[var(--muted)]">
              <Loader2 size={16} className="animate-spin" />
              Searching your events data...
            </div>
          )}
        </div>
        <div className="border-t border-[var(--border)] p-4">
          <p className="text-xs font-semibold text-[var(--muted)] mb-3">Quick questions</p>
          <div className="flex flex-wrap gap-2">
            {AI_ASSISTANT_RULES.map((rule) => (
              <button
                key={rule.id}
                type="button"
                onClick={() => void runRule(rule)}
                disabled={loading}
                className="px-3 py-1.5 text-sm bg-[var(--background)] border border-[var(--border)] text-[var(--foreground)] rounded-full hover:border-[var(--primary)] transition-colors disabled:opacity-50"
              >
                {rule.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
