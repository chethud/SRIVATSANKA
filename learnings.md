# Learnings

This file stores implementation learnings and verified response patterns derived from `D:\Kannan.rules.txt`.

Rules for this file:

- `D:\Kannan.rules.txt` is the primary authority.
- Only add notes that are explicitly supported by `D:\Kannan.rules.txt`.
- Do not invent new business logic, fallback copy, or chatbot states here.
- If this file ever conflicts with `D:\Kannan.rules.txt`, follow `D:\Kannan.rules.txt`.

## Verified Patterns

- The chatbot follows a strict 5-state flow: Greeting & Name, Event Type, Showcase vs Direct Planning, Parameter Gathering, Callback Scheduling & Sign-off.
- Every turn should run recovery check, multi-parameter entity sweep, then deterministic state transition execution.
- Multi-entity extraction must reuse all detected slots and skip unnecessary questions.
- The chatbot must not repeat already collected slots such as name, event, date, guest count, venue, meal type, or callback preference.
- Interrupt intents like discuss on call or call me should move directly to callback scheduling.
- Urgent timelines should skip remaining parameter gathering and fast-track to callback.
- Responses must stay short, warm, conversational, and must not use em-dashes.
- Event without name must ask for the name before showcase (STATE 1.5). Never advance to showcase on event alone.
- Polite fillers (`ok`, `yes`, `skip`) must never be stored as a customer name.
- Guest-count answers must never be stored as venue/location.
- Greeting-only repeats while waiting for a name must not burn the circuit-breaker loop budget.
- State 3 Intent B replies must be a single ack + date ask. Never stack `Got it! Let's jump...` with `Perfect! Let's get right down to planning...` in the same message.
- After showcase/portfolio/cuisine summary (Intent A), set `SHOWING_EVENT_INFORMATION` and close with `Type *DONE* to proceed.` Do not ask the date in that same message and do not ask the user to type `event`.
- `DONE` / `done` / `okay done` / `finished` / `continue` / `proceed` advance from `SHOWING_EVENT_INFORMATION` to event details (date). The same words must not complete a booking while already in event details.
- Invalid calendar dates stay in event details, keep name and other collected fields, and re-ask the date. Never circuit-break back to asking for the name.
- After capturing a name, ask a short Yes/No confirm (`Just checking, is your name {name}?`). Yes finalizes the name; No asks them to type the name again. Do not ask event/showcase questions until the name is confirmed.
- After the thank-you / sign-off, if the customer sends extra details, note them and reply moderately that a team member will call — do not reopen the form.
- After sign-off, `book again` / `another event` / `new booking` resets to STATE 1 so they can book another celebration.
- Dashboard: completed/converted orders have a **Book again** action that creates a new order with the same customer details.
- Prefer moderate reply length (1–3 short sentences): not overly polished essays, not one-word replies.
