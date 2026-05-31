# NDP demo — presentation & self-guided tutorial

End-to-end material that walks through the whole NDP system (installation, web
usage, the Python library, federation and the secure network), aimed at **end
users and administrators**.

## Files

- `NDP-demo-presentation.md` — the presentation in **Marp** format. It doubles as
  a self-guided tutorial: each step states what to do and what you will see.
- `assets/` — brand header/footer images (NDP logo + partner logos) reused from
  the official `ndp ep - presentation.pptx`. Applied to every slide via CSS.
- `screenshots/` — drop the screenshots here (see the checklist below).

## Turning it into slides

**Option A — VS Code (easiest):** install the **"Marp for VS Code"** extension,
open `NDP-demo-presentation.md` and click the preview icon. From there you can
export to **PDF**, **PPTX** (PowerPoint) or **HTML**.

**Option B — command line (Marp CLI):**

```bash
# --allow-local-files is required because the brand header/footer use local images
npx @marp-team/marp-cli --allow-local-files NDP-demo-presentation.md -o NDP-demo-presentation.pdf
npx @marp-team/marp-cli --allow-local-files NDP-demo-presentation.md --pptx -o NDP-demo-presentation.pptx
npx @marp-team/marp-cli NDP-demo-presentation.md -o NDP-demo-presentation.html
```

> Run these from inside `docs/demo/` so the `assets/...` paths resolve.

## Screenshots to capture

Each `[📸 screenshots/NN-name.png …]` placeholder in the presentation maps to one
screenshot. Checklist:

**Installation**
- [ ] `10-keycloak-login.png` — NDP login (Keycloak)
- [ ] `11-keycloak-admin.png` — Keycloak admin console (realm NDP)
- [ ] `12-affinities-frontend.png` — Affinities web app (relationships graph)
- [ ] `13-federation-ui.png` — federation web app (still empty)
- [ ] `14-ep-home.png` — Endpoint home page (search)
- [ ] `15-docker-ps.png` — `docker ps` with everything "Up"

**Identity and permissions**
- [ ] `19-keycloak-assign-ndp-admin.png` — assigning the `ndp_admin` realm role in Keycloak (first admin, full stack)
- [ ] `22-request-access.png` — user's "Request access" form (no role yet)
- [ ] `23-access-requests-approve.png` — admin Access Requests page approving with a tier

**Endpoint (web)**
- [ ] `30-search-ui.png` — Search page with options (category, catalog, filters)
- [ ] `33-create-resource.png` — example of a "+ New" creation form
- [ ] `34-search-results.png` — results with the dataset
- [ ] `35-viewer-vs-writer.png` — viewer vs writer menu (the key contrast)
- [ ] `36-s3-management.png` — S3 Management tool

**Python**
- [ ] `40-notebook.png` — notebook running the library

**Federation**
- [ ] `50-federation-ep-registered.png` — the EP in the federation
- [ ] `51-federation-health.png` — health/metrics

**NetBird (bonus)**
- [ ] `60-netbird-peers.png` — dashboard with connected peers
- [ ] `61-netbird-access.png` — accessing services over the mesh

**Appendix**
- [ ] `A1-affinities-add-endpoint.png` — Affinities "Add Endpoint" form (obtaining the EP_UUID)
- [ ] `A2-keycloak-create-user.png` — Keycloak: create user + set password (bootstrap)

## Notes

- Presentation text (and speaker notes `<!-- note: -->`) are in **English**.
- This material is written and refined incrementally (see issue #179).
