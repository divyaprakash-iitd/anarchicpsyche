# AnarchicPsyche

Hugo + [Blowfish](https://blowfish.page) blog, published to GitHub Pages on every push to `main`.

## First time: add the photos

```bash
python3 import_photos.py ~/Downloads/<wordpress-media-export>.tar
git add content assets && git commit -m "Add photos" && git push
```

Only the ~140 photos the posts use are copied, byte for byte (no resizing).

## Write a post

One folder per post, photos next to the text:

```
content/posts/my-new-trek/
  index.md
  feature.jpg      <- cover photo on the home page cards
  summit.jpg
```

`index.md`:

```markdown
---
title: "My New Trek"
date: 2026-12-01
categories: ["Travel Diaries"]
---

Text...

![](summit.jpg "Optional caption")

{{< photos >}}
left.jpg
right.jpg
{{< /photos >}}
```

- A photo on its own line shows full width (portrait shots up to 90% of the screen height), never cropped. Tap opens the original.
- `photos` puts several side by side at the same height.

## Preview locally (optional)

```bash
git submodule update --init
hugo server        # Hugo extended 0.166-0.169
```

## Comments

Readers can comment on every post with just a name (Waline on Vercel + Neon).
How it works and how to moderate: [docs/comments.md](docs/comments.md).
