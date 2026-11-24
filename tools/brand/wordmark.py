"""Turn the "anarchicpsyche" wordmark into SVG outlines, so no font is needed at runtime.

One-time step; the output (wordmark.json) is committed and read by build.mjs.
Font: Jost (SIL OFL), from the @fontsource/jost npm package.

  npm pack @fontsource/jost@5.2.5 && tar xzf fontsource-jost-5.2.5.tgz
  pip install fonttools brotli uharfbuzz
  python3 tools/brand/wordmark.py package/files > tools/brand/wordmark.json
"""
import io, json, sys
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

TEXT = "anarchicpsyche"
WEIGHTS = (200, 300)


def outline(path, text):
    tt = TTFont(path)
    tt.flavor = None  # woff2 -> sfnt bytes for HarfBuzz
    raw = io.BytesIO(); tt.save(raw)
    font = hb.Font(hb.Face(hb.Blob(raw.getvalue())))
    buf = hb.Buffer(); buf.add_str(text); buf.guess_segment_properties()
    hb.shape(font, buf, {"kern": True})  # kerning on
    glyphs, order, pen, x = tt.getGlyphSet(), tt.getGlyphOrder(), None, 0
    pen = SVGPathPen(glyphs)
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        # font units, y flipped so the baseline sits at y=0 with SVG's y-down axis
        glyphs[order[info.codepoint]].draw(
            TransformPen(pen, (1, 0, 0, -1, x + pos.x_offset, -pos.y_offset)))
        x += pos.x_advance
    return {"d": pen.getCommands(), "width": x, "xHeight": tt["OS/2"].sxHeight,
            "capHeight": tt["OS/2"].sCapHeight, "descender": -tt["hhea"].descent}


if __name__ == "__main__":
    files = sys.argv[1]
    out = {w: outline(f"{files}/jost-latin-{w}-normal.woff2", TEXT) for w in WEIGHTS}
    json.dump({"text": TEXT, "font": "Jost", "weights": out}, sys.stdout)
