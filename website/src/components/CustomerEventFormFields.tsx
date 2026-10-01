import { EVENT_TYPES, type CustomerEventFormState } from '../utils/eventTypes';

export function CustomerEventFormFields({
  form,
  setForm,
  showAdminNote = true,
}: {
  form: CustomerEventFormState;
  setForm: (next: CustomerEventFormState) => void;
  showAdminNote?: boolean;
}) {
  return (
    <>
      <input
        required
        placeholder="Customer name"
        value={form.customerName}
        onChange={(e) => setForm({ ...form, customerName: e.target.value })}
        className="form-input px-3 py-2 rounded-lg"
      />
      <input
        required
        placeholder="Phone number"
        value={form.phoneNumber}
        onChange={(e) => setForm({ ...form, phoneNumber: e.target.value })}
        className="form-input px-3 py-2 rounded-lg"
      />
      <select
        value={form.eventType}
        onChange={(e) => setForm({ ...form, eventType: e.target.value })}
        className="form-select px-3 py-2 rounded-lg"
      >
        {EVENT_TYPES.map((t) => (
          <option key={t} value={t}>{t}</option>
        ))}
      </select>
      <div>
        <label className="text-xs text-[var(--muted)] block mb-1">Event date (occasion)</label>
        <input
          required
          type="date"
          value={form.eventDate}
          onChange={(e) => setForm({ ...form, eventDate: e.target.value })}
          className="form-input w-full px-3 py-2 rounded-lg"
        />
      </div>
      <input
        required
        placeholder="Event location"
        value={form.eventLocation}
        onChange={(e) => setForm({ ...form, eventLocation: e.target.value })}
        className="form-input px-3 py-2 rounded-lg md:col-span-2"
      />
      <div className="md:col-span-2">
        <label className="text-xs text-[var(--muted)] block mb-1">Preferred callback</label>
        <input
          required
          type="datetime-local"
          value={form.preferredCallbackAt}
          onChange={(e) => setForm({ ...form, preferredCallbackAt: e.target.value })}
          className="form-input w-full px-3 py-2 rounded-lg"
        />
      </div>
      {showAdminNote && (
        <div className="md:col-span-2">
          <label className="text-xs text-[var(--muted)] block mb-1">Admin note</label>
          <textarea
            rows={2}
            value={form.adminNote}
            onChange={(e) => setForm({ ...form, adminNote: e.target.value })}
            placeholder="Internal note for this enquiry (not sent to customer)"
            className="form-input w-full px-3 py-2 rounded-lg resize-y"
          />
        </div>
      )}
    </>
  );
}
