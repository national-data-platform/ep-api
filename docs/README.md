# Documentation

Start here. This page lists every document in the repository, grouped by who it
is written for, with one line on what each one covers.

## Platform users

People who use an Endpoint through its UI or API, without running it.

- [info_for_nationaldataplatform/](info_for_nationaldataplatform/README.md) —
  drafts of the user-facing pages about the Endpoint, written for the central
  NDP documentation site:
  - [00 — What is an NDP Endpoint?](info_for_nationaldataplatform/00-what-is-an-endpoint.md)
  - [01 — Using an Endpoint](info_for_nationaldataplatform/01-using-an-endpoint.md)
  - [02 — Requesting access and the role tiers](info_for_nationaldataplatform/02-requesting-access-and-roles.md)
  - [03 — Publishing data](info_for_nationaldataplatform/03-publishing-data.md)
  - [04 — Automating with Python](info_for_nationaldataplatform/04-automating-with-python.md)
  - [05 — For institutional admins](info_for_nationaldataplatform/05-for-institutional-admins.md)
- [api-usage-guide.md](api-usage-guide.md) — the API by area (organizations,
  datasets, services, resources, search), with curl examples and responses.
- Tutorial notebooks, each a runnable walk-through against an Endpoint:
  - [general_dataset_api_tutorial.ipynb](general_dataset_api_tutorial.ipynb) — creating, searching, updating and deleting datasets.
  - [dogs_service_api_tutorial.ipynb](dogs_service_api_tutorial.ipynb) — registering and managing a service.
  - [s3_api_tutorial.ipynb](s3_api_tutorial.ipynb) — buckets and objects through the S3 routes.
  - [s3_to_dataset_workflow_tutorial.ipynb](s3_to_dataset_workflow_tutorial.ipynb) — from an object in S3 storage to a registered dataset.
  - [pelican_api_tutorial.ipynb](pelican_api_tutorial.ipynb) — browsing and reading from a Pelican federation.
- [demo/README.md](demo/README.md) — the NDP demo presentation, which doubles
  as a self-guided tutorial of the whole system, for users and administrators.

## Endpoint operators and administrators

People who install, configure and run an Endpoint.

- [../README.md](../README.md) — the project overview and quick start.
- [installing-with-the-script.md](installing-with-the-script.md) — installing
  an Endpoint with the installer, step by step.
- [../install/README.md](../install/README.md) — the installer in full: every
  flag, registration, remembered settings and how it works.
- [configuration.md](configuration.md) — every `.env` setting, what it does
  and its default.
- [operations.md](operations.md) — running an Endpoint: what runs, ports,
  where state lives, upgrading, backup, logs, health, common problems and a
  production security checklist.
- [roles-and-permissions.md](roles-and-permissions.md) — the role tiers, how
  roles reach the token and how to grant them.
- [affinities-integration.md](affinities-integration.md) — enabling the
  optional Affinities registration of datasets and services.
- [minio-setup.md](minio-setup.md) — setting up S3-compatible storage, with
  MinIO as the example.

## Developers

People who change the code.

- [development.md](development.md) — repository layout, local setup, running
  the tests as CI does, CI workflows, the release and change procedures, and
  code conventions.
- [architecture/overview.md](architecture/overview.md) — the overall
  architecture of the Endpoint.
- [architecture/federation-and-metrics.md](architecture/federation-and-metrics.md)
  — the Endpoint side of registration with the Federation, configuration by id
  and the metrics report.
- [architecture/connector-nodes-ep-inventory.md](architecture/connector-nodes-ep-inventory.md)
  — an inventory of the Endpoint's building blocks and whether each could be
  reused in a connector node.
- [sequence-diagrams/README.md](sequence-diagrams/README.md) — sequence
  diagrams of the main flows:
  - [installing-standalone-no-catalog.md](sequence-diagrams/installing-standalone-no-catalog.md) — installing a standalone Endpoint with no catalog.
  - [installing-registered-no-catalog.md](sequence-diagrams/installing-registered-no-catalog.md) — installing an Endpoint registered with the Federation.
  - [publishing-a-dataset.md](sequence-diagrams/publishing-a-dataset.md) — publishing a dataset.
  - [registering-and-using-a-service.md](sequence-diagrams/registering-and-using-a-service.md) — registering, reaching and publishing a service.
- [adding-catalog-backends.md](adding-catalog-backends.md) — implementing a
  new local catalog backend behind the repository interface.

## Project

- [../CHANGELOG.md](../CHANGELOG.md) — every release and what changed in it;
  the GitHub release notes are taken from it.
- [../CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md) — the code of conduct for
  contributors.

## Related projects

- **NDP Federation** ([github.com/sci-ndp/ndp-federation](https://github.com/sci-ndp/ndp-federation),
  private) — the installer can register an Endpoint with the Federation,
  installs it from the configuration the Federation returns for its id, and the
  Endpoint posts its periodic metrics to the Federation when `IS_PUBLIC` is
  true.
- **Affinities** ([github.com/sci-ndp/ndp-affinities](https://github.com/sci-ndp/ndp-affinities))
  — when `AFFINITIES_ENABLED` is true, the Endpoint registers the datasets and
  services it creates in Affinities, together with their links to this
  Endpoint.
