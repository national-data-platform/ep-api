# Sequence Diagrams

Each file here follows one process from beginning to end: who talks to whom, in
what order, and what is written or started along the way. One process per file.

The diagrams are [Mermaid](https://mermaid.js.org/syntax/sequenceDiagram.html)
`sequenceDiagram` blocks, which GitHub renders in place — every actor gets a
vertical lifeline and time runs downwards.

| Diagram | Shows |
|---|---|
| [Installing a standalone Endpoint with no catalog](installing-standalone-no-catalog.md) | The lightest install: no Federation registration, no local catalog, every answer left at its default, and the `.env` it produces |
| [Installing an Endpoint registered with the Federation](installing-registered-no-catalog.md) | The same install, registered: what the Federation creates on your behalf in Keycloak, the staging catalog and Affinities, and what of it the Endpoint actually uses |
| [Publishing a dataset](publishing-a-dataset.md) | Where a dataset goes — registered locally, promoted to the staging catalog, and why the global one is read-only — with every switch that stops it and the status code it produces |

For the static picture of the system — layers, routes, repositories — see
[../architecture-diagrams.md](../architecture-diagrams.md). These diagrams
complement it with the order things happen in.
