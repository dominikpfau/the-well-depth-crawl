# Depthcrawl Generator (Pyodide edition)

A dungeon/treasure generator that runs entirely client-side in the
browser via [Pyodide](https://pyodide.org/) (CPython compiled to
WebAssembly) - no backend server required for the finished app.

## Project layout

```
.
├── src/                    ← edit these files
│   ├── index.html          page shell (loads style.css / app.js)
│   ├── style.css           all styling
│   ├── app.js              glue code: Pyodide setup, event handlers
│   ├── data.py             game data (tables, descriptions) - unchanged logic
│   └── game.py             game logic + HTML rendering - unchanged logic
├── build.py                bundles src/ into a single distributable file
├── dist/
│   └── depthcrawl_pyodide.html   ← generated, this is what you ship/open
└── README.md
```

`data.py` and `game.py` are plain, ordinary Python files - your editor's
syntax highlighting, linting, and autocomplete all just work. Same for
`app.js` and `style.css`.

## Developing

Because browsers block `fetch()` of local files from a `file://` page,
`src/index.html` needs to be served over HTTP while you're working on
it (`app.js` loads `data.py`/`game.py` via `fetch`). Any static file
server works, e.g. Python's built-in one:

```bash
cd src
python3 -m http.server
```

Then open <http://localhost:8000/> in your browser. Edit `data.py`,
`game.py`, `app.js`, or `style.css` and just reload the page - no
build step needed during development.

## Building the standalone app

To produce the single-file version that can be opened directly
(double-click, `file://`, emailed as an attachment, etc.), run:

```bash
python3 build.py
```

This reads everything from `src/`, inlines `style.css`, `data.py`,
`game.py`, and `app.js` into `src/index.html`'s structure, and writes
the result to `dist/depthcrawl_pyodide.html`. That one file is fully
self-contained (it still needs internet access once, on first load,
to fetch Pyodide itself and the `markdown` package from a CDN/PyPI -
after that everything runs locally in the tab).

No third-party dependencies are needed to build - `build.py` only
uses the Python standard library.

## How it fits together

- `data.py` — all game data: location/detail tables, treasure tables,
  descriptions. No logic, just data.
- `game.py` — dice rolling, modifier aggregation, treasure/encounter
  generation, and a small set of `render_*` functions that build the
  HTML for the UI (replacing what used to be a Jinja2 template). Also
  holds `SESSION`, a module-level dict standing in for what used to be
  Flask's server-side session - there's only ever one "user" (the
  browser tab), so a plain global is enough.
- `app.js` — boots Pyodide, installs the `markdown` package via
  `micropip`, loads `data.py`/`game.py` into Pyodide's virtual
  filesystem, and wires up the buttons (`runAction`, `onLevelChange`)
  to call into Python (`game.handle_action`, `game.render_page`) and
  re-render `#app`'s HTML.
- `index.html` / `style.css` — page shell and styling.
- `build.py` — inlines everything from `src/` into one HTML file for
  distribution.

## Changing the Pyodide version

The Pyodide `<script>` URL (currently `v0.26.4`) is set in
`src/index.html`. Bump it there; `build.py` will pick up the change
automatically on the next build.
