# Sequence Diagrams

Each file here follows one process from beginning to end: who talks to whom, in
what order, and what is written or started along the way. One process per file.

The diagrams are [Mermaid](https://mermaid.js.org/syntax/sequenceDiagram.html)
`sequenceDiagram` blocks, which GitHub renders in place — every actor gets a
vertical lifeline and time runs downwards.

| Diagram | Shows |
|---|---|
| [Installing a standalone Endpoint with no catalog](installing-standalone-no-catalog.md) | The lightest install: no Federation registration, no local catalog, every answer left at its default, and the `.env` it produces |

For the static picture of the system — layers, routes, repositories — see
[../architecture-diagrams.md](../architecture-diagrams.md). These diagrams
complement it with the order things happen in.
