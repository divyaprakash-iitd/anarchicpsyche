# Anarchicpsyche blog: project notes for Claude

Personal blog (trek diaries + life stories), moved from anarchicpsyche.wordpress.com
to Hugo + Blowfish on GitHub Pages.

- Repo: divyaprakash-iitd/anarchicpsyche (public)
- Live: https://anarchicpsyche.me/ (custom domain set in repo Settings -> Pages; the old
  https://dpcfd.com/anarchicpsyche/ address redirects there)
- Owner: DP. Prefers concise, technical answers with code; clean minimal scripts.

## Working rules

- Work on a branch and open a PR; DP merges. Pushing to main triggers deploy.
- Never resize/recompress the original photos in the repo. Quality matters to DP.
- Editing post text: act like a human copy editor. Keep his voice (Hinglish words,
  informal phrasing, rhythm). Smallest fix; raise queries instead of rewriting.
  Only proofread/edit when asked.
- Drafts stay out of the repo (it's public). DP has them as a zip.

## Build and deploy

- `.github/workflows/hugo.yaml`: Hugo **0.169.0 extended** (Blowfish needs 0.166-0.169),
  checks out the theme submodule, caches `resources/_gen`, builds with
  `--baseURL` from configure-pages (forced to https), deploys to Pages.
- `config/_default/hugo.toml`: `timeout = "20m"` (first build resizes ~150 big photos on a
  2-core runner); `[imaging]` Lanczos, jpeg/webp quality 90;
  permalinks `posts = '/:year/:month/:day/:slug/'` (keeps old WordPress URLs).
- Local preview: `git submodule update --init && hugo server`.
- Published size ~643 MB; GitHub Pages limit is 1 GB. Watch this as posts grow.
- Harmless build warnings: "Unable to decode metadata" for 5 edited `-01` photos;
  Node 20 deprecation warnings on actions (bump action versions sometime).

## Layout customisations (all in this repo, theme untouched)

- `layouts/_default/_markup/render-image.html`: every Markdown image
  `![alt](file.jpg "caption")` becomes a full-bleed `<figure class="photo">`:
  landscape = full viewport width, portrait = max 90vh, never cropped.
  Missing file -> visible "Photo not added yet" box + build warning.
- `layouts/partials/photo-img.html`: srcset 960/1600/2560 + the original; `sizes`
  computed from aspect ratio; `data-zoom-src` = original, so Blowfish's medium-zoom
  opens the untouched original on tap.
- `layouts/partials/photo-oriented.html`: applies `images.AutoOrient` when EXIF
  orientation > 1 (guards for nil `.Meta` and GIFs).
- `layouts/shortcodes/photos.html`: side-by-side row, equal heights:
  ```
  {{< photos caption="optional" >}}
  a.jpg
  b.jpg
  {{< /photos >}}
  ```
- `assets/css/custom.css`: centres the reading column (41rem) so figures can break out
  with `margin-left: calc(50% - 50vw)`; `overflow-x: clip` on html/body; dark zoom overlay.
  Don't enable the TOC sidebar: it un-centres the column and breaks full-bleed photos.
- `config/_default/params.toml`: homepage `layout = "background"` with
  `assets/img/home.jpg`; cards on; article hero OFF (cover would duplicate the first
  photo); related posts, taxonomies, zen mode on; `showComments = false`;
  `showAuthorBottom = true` (DP doesn't want his name at the top);
  `defaultSocialImage = "img/social.png"`.
- `layouts/partials/home/background.html`: copy of the Blowfish v3.10.0 partial; only change
  is the homepage heading shows `assets/img/logo-stacked.svg` instead of the author name.
  Re-copy and re-apply if the theme is updated.
- `layouts/partials/favicons.html`: favicon/app-icon links (files in `static/`).

## Logo / brand

- `brand/`: logo suite (not published). `brand/original/ap_logo.png` = the WordPress logo,
  byte for byte. `brand/README.md` = usage, weights, colours.
- `tools/brand/build.js` generates everything (brand/svg, brand/png, site logo SVGs,
  favicons, social.png) from measured geometry. Run `node tools/brand/build.js`
  (Playwright + Chromium). Don't hand-edit generated files.
- Weights by size: fine (original strokes) >= 200 px, regular for header/hero, bold for app
  icons, tiny for 16-32 px favicons. Site SVGs use `currentColor` + `aria-hidden`.
- Wordmark: lowercase "anarchicpsyche" in Jost (OFL), outlined by `tools/brand/wordmark.py`
  into `wordmark.json`.

## Content

- 8 published posts as page bundles: `content/posts/<slug>/index.md` + photos.
  Cover photo = `feature.<ext>` in the bundle (Blowfish picks it up for cards).
- `tools/wp2hugo.py`: one-time WordPress XML -> Markdown converter (kept for record).
- `tools/photos.tsv` + `import_photos.py`: copied the 147 used originals out of the
  WordPress media export (byte for byte). `HOME_PHOTO` there chose the home background.
- 13 old WordPress comments were not migrated.

## Open tasks

1. **Comments -> Waline** (decided). Readers must be able to comment without any account.
   - Plan: Waline server on Vercel (Hobby, free, non-commercial only) + Neon Postgres
     (free). Avoid LeanCloud (shuts down 12 Jan 2027). DP sets up Vercel/Neon and
     registers first at `<serverURL>/ui/register` (first user = admin), then gives the
     serverURL.
   - Then: replace `layouts/partials/comments.html` (currently Cusdis, which is
     abandoned) with the Waline client (`@waline/client@v3` from unpkg, `init({ el,
     serverURL, path: location.pathname, dark: 'html.dark' })`), add a `walineServerURL`
     param, remove `cusdisAppId`, set `showComments = true`.
   - Delete the unmerged `cusdis-comments` branch.
   - Later, if the site becomes commercial (DP may sell trek photos): move Waline off
     Vercel Hobby, e.g. Heroku via GitHub Student Pack credits ($13/mo for 24 months;
     Procfile `web: node node_modules/@waline/vercel/vanilla.js $PORT`).
2. **Purge the WordPress XML from git history.** Commit `05e7e45` ("Add files via
   upload") contains `anarchicpsyche.WordPress.2026-11-21.xml` with 12 commenter emails,
   13 IPs and the drafts. It's removed from the tree but still in history. Needs a
   history rewrite + force-push. **Ask DP before doing it.**
3. **Proofreading** (only when DP asks): many typos per post (e.g. "Himalays",
   "Admist", "out journey" -> "our journey" in two posts). Also suggested: day-wise
   `##` headings in the long trek posts, a trek summary box (duration, start, highest
   point, season), fewer full-width photos with the rest in rows.
4. **Domain**: `anarchicpsyche.me` (bought Nov 2026). DNS at the registrar: apex A/AAAA
   records to GitHub Pages, `www` CNAME -> `divyaprakash-iitd.github.io`. Custom domain is set
   in repo Settings -> Pages (no CNAME file needed with Actions deploys); the workflow picks
   up the base URL from configure-pages. When Waline is set up, use this domain in
   `SITE_URL` / `SECURE_DOMAINS`.
5. Optional cleanup: delete merged branches (`site-setup`, `https-baseurl`,
   `fix-photo-meta`, `build-timeout`).
