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
