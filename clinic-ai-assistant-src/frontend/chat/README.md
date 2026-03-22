# Chat Layer

This folder is reserved for the chat shell shared by `index.html` and `cal.html`.

The chat shell owns:

- transcript append flow
- sender bubble rendering
- plain text and structured text rendering
- scroll-to-latest behavior
- lightweight DOM helpers for chat message containers
- page bootstrap helpers that are generic to chat pages

The chat shell must not own widget-specific rendering such as:

- booking progress UI
- booking summary cards
- slot button lists
- future calendar-like availability pickers
