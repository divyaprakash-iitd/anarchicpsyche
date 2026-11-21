#!/usr/bin/env python3
"""Copy the photos your posts use out of the WordPress media export.

    python3 import_photos.py ~/Downloads/<media-export>.tar

Works with the .tar (or .tar.gz / .zip) from WordPress, or a folder you
already unpacked. Files are copied byte for byte: no resizing, no
recompression. Only photos listed in tools/photos.tsv are copied, so the
rest of the export stays out of the repo. Safe to run again.
"""
import re
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HOME_PHOTO = "2018/06/heavenly_view.jpg"  # home page background; any photo from the export works
KEY = re.compile(r"(\d{4}/\d{2}/[^/]+)$")


def members(src):
    """Yield (name, open_function) for every file in the export, in one pass."""
    p = Path(src)
    if p.is_dir():
        for f in sorted(p.rglob("*")):
            if f.is_file():
                yield f.relative_to(p).as_posix(), f.open
    elif zipfile.is_zipfile(p):
        with zipfile.ZipFile(p) as z:
            for i in z.infolist():
                if not i.is_dir():
                    yield i.filename, lambda mode="rb", i=i: z.open(i)
    else:
        with tarfile.open(p, "r|*") as t:  # streaming: one pass through the archive
            for m in t:
                if m.isfile():
                    yield m.name, lambda mode="rb", m=m: t.extractfile(m)


def candidates(source):
    """The exact file, then WordPress's usual renamings of it."""
    name = source.rsplit("/", 1)[-1]
    stem, ext = name.rsplit(".", 1)
    yield source
    yield name
    for alt in (re.sub(r"-e\d{10,}$", "", stem), re.sub(r"-\d+$", "", stem)):
        if alt != stem:
            yield f"{alt}.{ext}"


def main(src):
    wanted = {}  # source -> [destination paths]
    for line in (ROOT / "tools" / "photos.tsv").read_text(encoding="utf-8").splitlines()[1:]:
        post_dir, file, source, _role = line.split("\t")
        dest = ROOT / post_dir / file
        if dest not in wanted.setdefault(source, []):
            wanted[source].append(dest)
    wanted.setdefault(HOME_PHOTO, []).append(ROOT / "assets" / "img" / ("home." + HOME_PHOTO.rsplit(".", 1)[1]))

    # 1st pass: list the export so renamed files can be matched
    names = {}
    for name, _ in members(src):
        m = KEY.search(name)
        if m:
            names.setdefault(m.group(1), name)
            names.setdefault(m.group(1).rsplit("/", 1)[-1], name)
    plan, missing = {}, []
    for source, dests in wanted.items():
        hit = next((names[c] for c in candidates(source) if c in names), None)
        if hit:
            plan.setdefault(hit, []).extend(dests)
        else:
            missing.append(source)

    # 2nd pass: copy
    copied = skipped = size = 0
    for name, open_ in members(src):
        if name not in plan:
            continue
        with open_("rb") as f:
            data = f.read()
        for dest in plan[name]:
            dest.parent.mkdir(parents=True, exist_ok=True)
            size += len(data)
            if dest.exists() and dest.stat().st_size == len(data):
                skipped += 1
                continue
            dest.write_bytes(data)
            copied += 1

    print(f"copied {copied}, already there {skipped}, {size / 1e6:.0f} MB in posts")
    if missing:
        print("\nnot found in the export:")
        for s in missing:
            print("  " + s)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
