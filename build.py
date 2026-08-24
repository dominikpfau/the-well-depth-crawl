#!/usr/bin/env python3
"""
Bundles the developer-friendly `src/` project into a single,
self-contained `dist/depthcrawl_pyodide.html` file that can be opened
directly (double-click / file://) without any server.

Usage:
    python3 build.py

What it does:
    - Reads src/index.html as the page template.
    - Inlines src/style.css into a <style> block
      (replacing the <link rel="stylesheet" ...> tag).
    - Inlines src/data.py and src/game.py as
      <script type="text/python" id="py-data"> / id="py-game">
      blocks (these are never executed as JS by the browser -
      app.js reads their textContent and hands it to Pyodide).
    - Inlines src/app.js into a <script> block
      (replacing <script src="app.js"></script>).
    - Writes the result to dist/depthcrawl_pyodide.html.

No third-party dependencies - only the Python standard library.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
DIST = ROOT / "dist"

STYLE_LINK_TAG = '<link rel="stylesheet" href="style.css">'
APP_SCRIPT_TAG = '<script src="app.js"></script>'


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def replace_once(html: str, needle: str, replacement: str, description: str) -> str:
    count = html.count(needle)
    if count != 1:
        raise SystemExit(
            f"Expected exactly one occurrence of {description!r} in "
            f"src/index.html, found {count}. Did the template change? "
            "Update build.py to match."
        )
    return html.replace(needle, replacement)


def build() -> Path:
    index_html = read(SRC / "index.html")
    style_css = read(SRC / "style.css")
    app_js = read(SRC / "app.js")
    data_py = read(SRC / "data.py")
    game_py = read(SRC / "game.py")

    # Inline the stylesheet.
    index_html = replace_once(
        index_html,
        STYLE_LINK_TAG,
        f"<style>\n{style_css}\n</style>",
        "the stylesheet <link> tag",
    )

    # Inline data.py / game.py as non-executable <script type="text/python">
    # blocks, followed by the actual app.js logic. app.js's
    # loadPythonSource() picks these up automatically instead of
    # fetch()-ing the .py files, so no code changes are needed there.
    python_blocks = (
        f'<script type="text/python" id="py-data">\n{data_py}\n</script>\n\n'
        f'<script type="text/python" id="py-game">\n{game_py}\n</script>\n\n'
    )
    index_html = replace_once(
        index_html,
        APP_SCRIPT_TAG,
        python_blocks + f"<script>\n{app_js}\n</script>",
        "the app.js <script> tag",
    )

    DIST.mkdir(exist_ok=True)
    out_path = DIST / "depthcrawl_pyodide.html"
    out_path.write_text(index_html, encoding="utf-8")
    return out_path


if __name__ == "__main__":
    output = build()
    size_kb = output.stat().st_size / 1024
    print(f"Built {output.relative_to(ROOT)} ({size_kb:.1f} KB)")
