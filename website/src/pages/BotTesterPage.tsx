import { useState } from 'react';
import { Send } from 'lucide-react';
import { PageHeader } from '../components/Layout';
import { useAppData } from '../context/AppDataContext';
import { testBotMessage, type BotTestResponse } from '../api/client';

interface ChatMessage {
  role: 'user' | 'bot';
  text: string;
  media?: BotTestResponse['media'];
}

export default function BotTesterPage() {
  const { refresh } = useAppData();
  const [phone] = useState('919999999999');
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);

  async function sendMessage(text: string) {
    if (!text.trim() || loading) return;
    setMessages((prev) => [...prev, { role: 'user', text }]);
    setInput('');
    setLoading(true);

    try {
      const res = await testBotMessage(phone, text);
      setMessages((prev) => [
        ...prev,
        { role: 'bot', text: res.reply, media: res.media },
      ]);
      if (res.enquiry_saved) refresh();
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'bot', text: 'Error: Could not reach FastAPI. Run uvicorn on port 8000.' },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <PageHeader
        title="WhatsApp Bot Tester"
        description="Simulate customer conversations with the FastAPI AI agent"
      />
      <p className="text-sm text-[var(--muted)] mb-4">
        Flow: Hi → name → company → event type → photos → ask questions freely → reply <strong>ok</strong> →
        event details → cuisine. Send <strong>new</strong> to restart.
      </p>
      <div className="bg-[var(--card)] border border-[var(--border)] rounded-xl flex flex-col h-[520px] max-w-2xl">
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 ? (
            <p className="text-[var(--muted)] text-center mt-16">
              Start with &quot;Hi&quot; — after event photos you can ask questions before typing &quot;ok&quot;.
            </p>
          ) : (
            messages.map((msg, i) => (
              <div
                key={i}
                className={`max-w-[85%] ${msg.role === 'user' ? 'ml-auto' : ''}`}
              >
                <div
                  className={`p-3 rounded-xl text-sm whitespace-pre-wrap ${
                    msg.role === 'user'
                      ? 'bg-[#dcf8c6] text-[#111]'
                      : 'bg-[var(--background)] border border-[var(--border)]'
                  }`}
                >
                  {msg.text}
                </div>
                {msg.media && msg.media.length > 0 && (
                  <div className="mt-2 grid grid-cols-1 gap-2">
                    {msg.media.map((m, j) => (
                      <figure key={j} className="rounded-lg overflow-hidden border border-[var(--border)]">
                        <img
                          src={m.url}
                          alt={m.caption || 'Event photo'}
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
            ))
          )}
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            sendMessage(input);
          }}
          className="border-t border-[var(--border)] p-4 flex gap-3"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type as a customer..."
            disabled={loading}
            className="form-input flex-1 px-4 py-2 rounded-lg outline-none focus:border-[var(--primary)] disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 bg-[var(--primary)] text-white rounded-lg hover:bg-[var(--primary-hover)] disabled:opacity-50"
          >
            <Send size={18} />
          </button>
        </form>
      </div>
    </>
  );
}
