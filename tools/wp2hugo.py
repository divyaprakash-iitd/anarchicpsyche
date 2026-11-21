#!/usr/bin/env python3
"""One-time conversion of the WordPress.com export (WXR XML) into Hugo page bundles.

    python3 tools/wp2hugo.py anarchicpsyche.WordPress.2026-11-21.xml

Writes content/posts/<slug>/index.md for every published post, drafts to
drafts/<slug>/index.md (git-ignored), and tools/photos.tsv, the list of photos each post needs. import_photos.py
reads that list to copy the original files out of the media export.
Needs: beautifulsoup4, markdownify.
"""
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag
from markdownify import markdownify

NS = {
    "wp": "http://wordpress.org/export/1.2/",
    "content": "http://purl.org/rss/1.0/modules/content/",
}
UPLOADS = re.compile(r"/wp-content/uploads/(\d{4}/\d{2}/[^?#\"']+)")
FILENAME_ALT = re.compile(r"^(img|dsc|photo|pxl|vid)?[_\- ]?[\d_\-]+(\.\w+)?$", re.I)


def text(item, path):
    return item.findtext(path, namespaces=NS) or ""


def meta(item, key):
    for m in item.findall("wp:postmeta", NS):
        if text(m, "wp:meta_key") == key:
            return text(m, "wp:meta_value")
    return ""


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "untitled"


def yaml_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def wpautop(html):
    """Classic-editor posts store bare text; blank lines separate paragraphs."""
    out = []
    for chunk in re.split(r"\n\s*\n", html.strip()):
        chunk = chunk.strip()
        if not chunk:
            continue
        if re.match(r"(?is)^<(p|div|h\d|ul|ol|figure|blockquote|hr)\b", chunk):
            out.append(chunk)
        elif re.fullmatch(r"(?is)(\s*(<a[^>]*>)?\s*<img[^>]*>\s*(</a>)?\s*)+", chunk):
            out.append('<div class="wp-row">' + chunk + "</div>")
        else:
            out.append("<p>" + chunk.replace("\n", "<br>\n") + "</p>")
    return "\n".join(out)


class Post:
    def __init__(self, item, attachments, tz_offset):
        self.item = item
        self.photos = []  # (local_name, source_path, role)
        self._names = {}  # local_name -> source_path
        self.attachments = attachments
        self.tz = tz_offset

    def local_name(self, source):
        name = source.rsplit("/", 1)[-1]
        if self._names.get(name, source) != source:  # same name, different month
            name = source[:7].replace("/", "-") + "-" + name
        if name not in self._names:
            self._names[name] = source
            self.photos.append((name, source, "body"))
        return name

    def photo(self, img):
        m = UPLOADS.search(img.get("data-url") or img.get("src") or "")
        if not m:
            return None
        return self.local_name(m.group(1))

    # --- HTML -> Markdown -------------------------------------------------
    def convert(self, html):
        html = re.sub(r"<!--\s*/?wp:.*?-->", "", html, flags=re.S)
        # classic-editor [caption]<img> text[/caption] -> <figure>
        html = re.sub(
            r"\[caption[^\]]*\]\s*((?:<a[^>]*>)?\s*<img[^>]*>\s*(?:</a>)?)(.*?)\[/caption\]",
            r"<figure>\1<figcaption>\2</figcaption></figure>", html, flags=re.S)
        if "<p" not in html and "<figure" not in html:
            html = wpautop(html)
        soup = BeautifulSoup(html, "html.parser")
        parts = []
        self.walk(soup, parts)
        md = "\n\n".join(p.strip() for p in parts if p.strip())
        return re.sub(r"\n{3,}", "\n\n", md) + "\n"

    def walk(self, node, parts):
        for el in list(node.children):
            if isinstance(el, NavigableString):
                if el.strip():
                    parts.append(markdownify(str(el)))
                continue
            if not isinstance(el, Tag):
                continue
            imgs = el.find_all("img") if el.name != "img" else [el]
            has_text = el.get_text(" ", strip=True)
            if el.name == "hr":
                parts.append("---")
            elif imgs and not has_text or (imgs and el.name == "figure"):
                parts.append(self.photos_md(el, imgs))
            elif imgs:  # text and photos mixed: go one level down
                self.walk(el, parts)
            elif el.name in ("div", "section"):
                self.walk(el, parts)
            elif has_text:
                parts.append(self.text_md(el))

    def text_md(self, el):
        for t in el.find_all(True):
            t.attrs.pop("style", None)
            t.attrs.pop("class", None)
        md = markdownify(str(el), heading_style="ATX", bullets="-")
        return md.replace(" ", " ")

    def photos_md(self, el, imgs):
        names, alts = [], []
        for img in imgs:
            n = self.photo(img)
            if n:
                names.append(n)
                alt = (img.get("alt") or "").strip()
                stem = re.sub(r"[\W_]+", "", Path(n).stem.lower())
                junk = (FILENAME_ALT.match(alt) or alt.startswith("This image has an empty alt")
                        or re.sub(r"[\W_]+", "", alt.lower()) == stem)
                alts.append("" if junk else alt)
        if not names:
            return ""
        cap = " ".join(markdownify(c.decode_contents()).strip() for c in el.find_all("figcaption"))
        cap = re.sub(r"\s+", " ", cap).strip()
        cls = " ".join(el.get("class") or [])
        row = len(names) > 1 and (
            "tiled-gallery" in cls or "image-compare" in cls or "wp-row" in cls
            or el.find(class_="juxtapose") is not None
        )
        if row:
            capa = f" caption={yaml_str(cap)}" if cap else ""
            return f"{{{{< photos{capa} >}}}}\n" + "\n".join(names) + "\n{{< /photos >}}"
        out = []
        for i, (n, a) in enumerate(zip(names, alts)):
            c = cap if (i == len(names) - 1) else ""
            title = f' {yaml_str(c)}' if c else ""
            out.append(f"![{a}]({n}{title})")
        return "\n\n".join(out)

    # --- page bundle ------------------------------------------------------
    def write(self, root):
        it = self.item
        title = (it.findtext("title") or "").strip() or "Untitled"
        slug = text(it, "wp:post_name") or slugify(title)
        draft = text(it, "wp:status") != "publish"
        local = datetime.strptime(text(it, "wp:post_date"), "%Y-%m-%d %H:%M:%S")
        cats = [c.text for c in it.findall("category")
                if c.get("domain") == "category" and c.text != "Uncategorized"]
        tags = [c.text for c in it.findall("category") if c.get("domain") == "post_tag"]

        body = self.convert(text(it, "content:encoded"))
        # links to other posts on the old blog -> relative links on the new site
        here = local.strftime("%Y/%m/%d/") + slug + "/"
        body = re.sub(
            r"https?://anarchicpsyche\.wordpress\.com/(\d{4}/\d{2}/\d{2}/[\w\-]+/?)",
            lambda m: "../" * here.count("/") + m.group(1).rstrip("/") + "/", body)

        thumb = self.attachments.get(meta(it, "_thumbnail_id"))
        if thumb:
            self.photos.append(("feature" + Path(thumb).suffix.lower(), thumb, "feature"))
        elif any(r == "body" for _, _, r in self.photos):
            first = next(s for _, s, r in self.photos if r == "body")
            self.photos.append(("feature" + Path(first).suffix.lower(), first, "feature"))

        fm = ["---", f"title: {yaml_str(title)}",
              f"date: {local.isoformat()}{self.tz}",
              f"slug: {yaml_str(slug)}"]
        if cats:
            fm.append("categories: [" + ", ".join(yaml_str(c) for c in cats) + "]")
        if tags:
            fm.append("tags: [" + ", ".join(yaml_str(t) for t in tags) + "]")
        fm += [f"draft: {str(draft).lower()}", "---", ""]

        # drafts stay out of the public repo (drafts/ is git-ignored)
        d = root / ("drafts" if draft else "content/posts") / slug
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.md").write_text("\n".join(fm) + "\n" + body, encoding="utf-8")
        return d, title, draft


def main(xml_path):
    root = Path(__file__).resolve().parent.parent
    ch = ET.parse(xml_path).getroot().find("channel")
    items = ch.findall("item")

    attachments = {}
    for it in items:
        if text(it, "wp:post_type") == "attachment":
            m = UPLOADS.search(text(it, "wp:attachment_url"))
            if m:
                attachments[text(it, "wp:post_id")] = m.group(1)

    rows = []
    for it in items:
        if text(it, "wp:post_type") != "post":
            continue
        local = datetime.strptime(text(it, "wp:post_date"), "%Y-%m-%d %H:%M:%S")
        gmt = text(it, "wp:post_date_gmt")
        off = 0
        if gmt and not gmt.startswith("0000"):
            off = round((local - datetime.strptime(gmt, "%Y-%m-%d %H:%M:%S")).total_seconds() / 900) * 15
        tz = "Z" if off == 0 else f"{'+' if off > 0 else '-'}{abs(off)//60:02d}:{abs(off)%60:02d}"
        p = Post(it, attachments, tz)
        d, title, draft = p.write(root)
        rel = d.relative_to(root).as_posix()
        if not draft:
            rows += [f"{rel}\t{n}\t{s}\t{r}" for n, s, r in p.photos]
        print(f"{'draft' if draft else 'post '}  {rel}  ({sum(r == 'body' for *_, r in p.photos)} photos)  {title}")

    (root / "tools" / "photos.tsv").write_text(
        "post_dir\tfile\tsource\trole\n" + "\n".join(rows) + "\n", encoding="utf-8")
    print(f"\n{len(rows)} photo entries -> tools/photos.tsv")


if __name__ == "__main__":
    main(sys.argv[1])
