/** Predefined dashboard AI queries — matches backend rules in dashboard_assistant.py */
export type AiAssistantRule = {
  id: string;
  label: string;
  query: string;
};

export const AI_ASSISTANT_RULES: AiAssistantRule[] = [
  { id: 'upcoming', label: 'Upcoming events', query: 'Show all upcoming events' },
  { id: 'wedding', label: 'Wedding enquiries', query: 'Show wedding enquiries' },
  { id: 'birthday', label: 'Birthday enquiries', query: 'Show birthday enquiries' },
  { id: 'corporate', label: 'Corporate enquiries', query: 'Show corporate enquiries' },
  { id: 'guests-200', label: '200+ guests', query: 'Show enquiries above 200 guests' },
  { id: 'recent', label: 'Recent enquiries', query: 'Show recent enquiries' },
  { id: 'summary', label: 'Business summary', query: 'Business summary' },
];

export function renderMarkdownish(text: string) {
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
      </span>
    );
  });
}
