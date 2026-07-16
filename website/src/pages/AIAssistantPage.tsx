import { useState } from 'react';
import { Send, Loader2 } from 'lucide-react';
import { PageHeader } from '../components/Layout';
import { askDashboardAssistant } from '../api/client';

const exampleQueries = [
  'Show all upcoming events',
  'Show wedding enquiries',
  'Show enquiries above 200 guests',
  'Business summary',
  'Show recent enquiries',
];

function renderMarkdownish(text: string) {
  return text.split('\n').map((line, i) => {
    const parts = line.split(/(\*\*[^*]+\*\*|_[^_]+_)/g).map((part, j) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={j}>{part.slice(2, -2)}</strong>;
      }
      if (part.startsWith('_') && part.endsWith('_')) {
        return <em key={j}>{part.slice(1, -1)}</em>;
      }
      return part;
    });
    return (
      <span key={i} className="block whitespace-pre-wrap">
        {parts}
        {i < text.split('\n').length - 1 ? null : null}
      </span>
    );
  });
}

export default function AIAssistantPage() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<{ role: 'user' | 'assistant'; text: string }[]>([]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const text = query.trim();
    if (!text || loading) return;

    setQuery('');
    setMessages((prev) => [...prev, { role: 'user', text }]);
    setLoading(true);

    try {
      const { reply } = await askDashboardAssistant(text);
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
        description="Ask questions about enquiries, upcoming events, and business stats"
      />
      <div className="flex flex-wrap gap-2 mb-6">
        {exampleQueries.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => setQuery(q)}
            className="px-3 py-1.5 text-sm bg-[var(--card)] border border-[var(--border)] text-[var(--foreground)] rounded-full hover:border-[var(--primary)] transition-colors"
          >
            {q}
          </button>
        ))}
      </div>
      <div className="bg-[var(--card)] border border-[var(--border)] rounded-xl flex flex-col h-[500px] shadow-sm">
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 ? (
            <p className="text-[var(--muted)] text-center mt-20">
              Try &quot;Show all upcoming events&quot; to see live enquiry data
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
        <form onSubmit={handleSubmit} className="border-t border-[var(--border)] p-4 flex gap-3">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask a question..."
            disabled={loading}
            className="form-input flex-1 px-4 py-2 rounded-lg outline-none focus:border-[var(--primary)] disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="px-4 py-2 bg-[var(--primary)] text-white rounded-lg hover:bg-[var(--primary-hover)] transition-colors disabled:opacity-50"
          >
            <Send size={18} />
          </button>
        </form>
      </div>
    </>
  );
}
