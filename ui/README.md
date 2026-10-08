# NDP Endpoint web UI

The React web interface of the NDP Endpoint. It lives in this directory of the
[ep-api](https://github.com/national-data-platform/ep-api) repository and is
not deployed on its own: it is built into the Endpoint's Docker image and
served by the same container as the API.

From the UI, users sign in and work with the Endpoint's API: search, datasets,
organizations, URL / S3 / Kafka resources, services, S3 buckets and objects,
and, for admins, access requests. What a user may do is decided by the API
(see [../docs/roles-and-permissions.md](../docs/roles-and-permissions.md)); the
UI reads the user's `effective_role` from `GET /user/info` to decide which
actions to show.

## How it is built and served

- [Dockerfile.allinone](../Dockerfile.allinone), stage 1 (`node:18-alpine`),
  runs `npm ci` and `npm run build` here; the build is copied to
  `/app/ui/build` in the final image.
- nginx serves it at `${ROOT_PATH}/ui/` (`package.json` sets
  `"homepage": "/ui"`).
- API calls are relative to the page's origin, prefixed with `ROOT_PATH`, so
  the UI always talks to the API of the container that served it. No API URL
  is configured.

## Runtime configuration

At every container start, [entrypoint.sh](../entrypoint.sh) writes
`/app/ui/build/config.js`, loaded by `public/index.html`, which sets
`window.__EP_CONFIG__` from the container's environment:

| Key | From |
|---|---|
| `rootPath` | `ROOT_PATH` |
| `affinitiesEpUuid` | `AFFINITIES_EP_UUID` |
| `oidcEnabled` | `OIDC_ENABLED` (default `False`) |
| `oidcIssuer`, `oidcClientId`, `oidcScope` | `OIDC_ISSUER`, `OIDC_CLIENT_ID`, `OIDC_SCOPE` |
| `oidcButtonLabel`, `oidcHelpText` | `OIDC_BUTTON_LABEL`, `OIDC_HELP_TEXT` |

It also rewrites the `/ui/` asset paths in `index.html` to
`${ROOT_PATH}/ui/`. These variables are documented in
[../docs/configuration.md](../docs/configuration.md).

## Development

Node 18, as in the image and in CI:

```bash
npm ci
npm test -- --watchAll=false   # what CI runs
npm run build                  # production build into build/
```

`npm start` runs the `react-scripts` development server. No proxy is
configured and `config.js` is only generated inside the container, so a page
served by the development server sends its API calls to the development
server itself.

To see a UI change in a running Endpoint, rebuild the image from the
repository root (`docker compose up -d --build`).

## License

MIT — see [../LICENSE](../LICENSE).
