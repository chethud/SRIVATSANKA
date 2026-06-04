import { useState } from 'react';
import { Send } from 'lucide-react';
import { PageHeader } from '../components/Layout';
import { useAppData } from '../context/AppDataContext';
import { testBotMessage } from '../api/client';

interface ChatMessage {
  role: 'user' | 'bot';
  text: string;
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
      setMessages((prev) => [...prev, { role: 'bot', text: res.reply }]);
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
        Full flow: event details → dish categories → dish selection → customizations → saved to Enquiries page.
        Send <strong>new</strong> to restart. Use a new phone number for a fresh session.
      </p>
      <div className="bg-[var(--card)] border border-[var(--border)] rounded-xl flex flex-col h-[520px] max-w-2xl">
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 ? (
            <p className="text-[var(--muted)] text-center mt-16">
              Try: &quot;Hi&quot; then answer each question, then pick categories like &quot;1,5&quot; and dishes like &quot;1,2&quot;
            </p>
          ) : (
            messages.map((msg, i) => (
              <div
                key={i}
                className={`max-w-[85%] p-3 rounded-xl text-sm whitespace-pre-wrap ${
                  msg.role === 'user'
                    ? 'ml-auto bg-[#dcf8c6] text-[#111]'
                    : 'bg-[var(--background)] border border-[var(--border)]'
                }`}
              >
                {msg.text}
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
            className="flex-1 px-4 py-2 border border-[var(--border)] rounded-lg outline-none focus:border-[var(--primary)] disabled:opacity-50"
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
