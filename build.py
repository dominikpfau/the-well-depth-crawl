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


def assert_safe_to_embed(text: str, source_name: str, forbidden: str) -> None:
    """
    Guards against the classic "content contains its own closing tag"
    bug: HTML's <script>/<style> elements are parsed as raw text up
    to the *first* occurrence of their closing tag - the parser does
    not understand nesting. If e.g. app.js contains the literal
    string "</script>" anywhere (even inside a comment or a string
    literal), embedding it inside a real <script> element will cut
    the element short right there, and the rest of the file spills
    out as visible page text.

    This scans case-insensitively, matching how browsers do it.
    """
    lower_text = text.lower()
    idx = lower_text.find(forbidden.lower())
    if idx != -1:
        line_no = text.count("\n", 0, idx) + 1
        raise SystemExit(
            f"Refusing to build: {source_name} contains the literal "
            f"sequence {forbidden!r} on line {line_no}. Embedding this "
            f"file verbatim into the page would prematurely close the "
            f"surrounding tag and break the output. Rephrase/escape it "
            f"(e.g. split the string, or avoid a literal '{forbidden}') "
            f"and rebuild."
        )


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

    # Guard against accidentally embedding a closing tag inside content
    # that will be wrapped in that very tag (see docstring above).
    assert_safe_to_embed(style_css, "src/style.css", "</style")
    assert_safe_to_embed(app_js, "src/app.js", "</script")
    assert_safe_to_embed(data_py, "src/data.py", "</script")
    assert_safe_to_embed(game_py, "src/game.py", "</script")

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
