# NDP demo — presentation & self-guided tutorial

End-to-end material that walks through the whole NDP system (installation, web
usage, the Python library, federation and the secure network), aimed at **end
users and administrators**.

## Files

- `NDP-demo-presentation.md` — the presentation in **Marp** format. It doubles as
  a self-guided tutorial: each step states what to do and what you will see.
- `assets/` — brand header/footer images (NDP logo + partner logos) reused from
  the official `docs/ndp ep - presentation.pptx` and applied to every slide via
  CSS; the component icons (`assets/icons/`) and the component-interactions
  diagram (`assets/diagrams/`).
- `screenshots/` — the screenshots shown in the presentation (listed below).

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

## Screenshots

`screenshots/` holds the images the presentation shows, each on its own
full-slide ("imgslide") slide after the slide it illustrates:

**Installation**
- `12-affinities-frontend.png` — Affinities web app
- `13-federation-ui.png` — Federation admin dashboard
- `15-docker-ps.png` — `docker ps` with every container "Up"
- `14-ep-home.png` — the Endpoint's Search landing page

**Identity and permissions**
- `22-request-access.png` — "Request access to this Endpoint" form shown to a refused user
- `23-access-requests-approve.png` — admin Access Requests page approving with a tier

**Endpoint (web)**
- `30-search-ui.png` — Search page with its options (category, catalog, My assets)
- `33-create-resource.png` — the filled "New dataset" form
- `34-search-results.png` — Local search for "nexrad" showing the new dataset
- `36-s3-management.png` — S3 Management page

**Federation**
- `50-federation-ep-registered.png` — Federation admin "Endpoints" list with the Endpoint
- `51-federation-health.png` — Federation admin "Metrics" list

**Appendix**
- `A1-affinities-add-endpoint.png` — Affinities "Add Endpoint" form (obtaining an Affinities UID)

## Notes

- Presentation text (and speaker notes `<!-- note: -->`) are in **English**.
- This material is written and refined incrementally (see issue #179); it was
  last checked against ep-api v0.34.47 (issue #338).
