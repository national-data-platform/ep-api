# `info_for_nationaldataplatform/`

Drafts of documentation pages about the **NDP Endpoint (EP)**, written to slot
into the central NDP documentation site at
[nationaldataplatform.org/documentation/](https://nationaldataplatform.org/documentation/)
(suggested location: `/documentation/ndp-ep/...`).

These files are plain Markdown — no site-specific front-matter — so they can be
included by any static site generator the documentation site uses.

## Pages

| # | File | Audience | What it covers |
|---|---|---|---|
| 00 | [`00-what-is-an-endpoint.md`](00-what-is-an-endpoint.md) | Everyone | What an NDP-EP is and where it fits in the federation. |
| 01 | [`01-using-an-endpoint.md`](01-using-an-endpoint.md) | Researchers, educators | Finding and using an Endpoint as a logged-in NDP user. |
| 02 | [`02-requesting-access-and-roles.md`](02-requesting-access-and-roles.md) | Users who want to publish | The access-request workflow and the viewer / writer / admin tiers. |
| 03 | [`03-publishing-data.md`](03-publishing-data.md) | Writers | The `+ New` flows — organizations, datasets, URL / S3 / Kafka resources, services. |
| 04 | [`04-automating-with-python.md`](04-automating-with-python.md) | Power users, data engineers | Using the `ndp-ep` Python library for automation and bulk loading. |
| 05 | [`05-for-institutional-admins.md`](05-for-institutional-admins.md) | Institutional IT, data-ops | How an institution obtains an Endpoint, what NDP provides vs. what the institution provides. |

## Status

These are drafts maintained alongside the Endpoint API source, so changes to the
EP (UI, API, configuration) keep them in sync. When the central documentation
site picks them up, the canonical copy lives there.
