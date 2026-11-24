"""Download YouTube thumbnails for the Videos page into assets/img/videos/<id>.jpg.

Run after adding videos to data/videos.yaml (needs PyYAML):

  python3 tools/video_thumbs.py

Existing files are kept. Videos get the 1280x720 thumbnail, Shorts the vertical
1080x1920 one. Hugo serves resized copies; without a file here the page falls back
to YouTube's own thumbnail.
"""
import pathlib, urllib.request, yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "img" / "videos"

data = yaml.safe_load((ROOT / "data" / "videos.yaml").read_text())
OUT.mkdir(parents=True, exist_ok=True)
for group in data["groups"]:
    name = "oar2.jpg" if group.get("short") else "maxresdefault.jpg"
    for video in group["videos"]:
        path = OUT / f"{video['id']}.jpg"
        if path.exists():
            continue
        url = f"https://i.ytimg.com/vi/{video['id']}/{name}"
        try:
            path.write_bytes(urllib.request.urlopen(url, timeout=30).read())
            print("got", path.name)
        except Exception as e:  # keep going; the page falls back to YouTube's thumbnail
            print("FAILED", url, e)
