let pyGame = null;

function showError(err) {
    const box = document.getElementById("error-box");
    box.style.display = "block";
    box.textContent = "Fehler:\n" + err;
    document.getElementById("loading").style.display = "none";
}

function getDepth() {
    const el = document.getElementById("depth");
    if (!el || el.value === "") return 0;
    const n = parseInt(el.value, 10);
    return Number.isNaN(n) ? 0 : n;
}

function getLevel() {
    const el = document.getElementById("level");
    if (!el || el.value === "") return null;
    return el.value;
}

function renderApp() {
    const html = pyGame.render_page();
    document.getElementById("app").innerHTML = html;
}

async function runAction(action) {
    try {
        pyGame.handle_action(action, String(getDepth()), getLevel());
        renderApp();
    } catch (err) {
        showError(err);
    }
}

async function onLevelChange() {
    try {
        pyGame.handle_action(null, String(getDepth()), getLevel());
        renderApp();
    } catch (err) {
        showError(err);
    }
}

/**
 * Loads one of our Python source files.
 *
 * Two ways this can be satisfied, so the exact same app.js works both
 * during development and in the bundled single-file build:
 *
 *   1. Bundled build (dist/depthcrawl_pyodide.html): build.py has
 *      inlined the file's content into a "text/python" script
 *      element with a matching id, right in the page. We just read
 *      its textContent - no network request, works fine from a
 *      plain file:// URL.
 *
 *   2. Dev mode (src/index.html served via a local static server):
 *      that inline element doesn't exist, so we fall back to
 *      fetching the .py file directly. This requires the page to be
 *      served over http(s):// (browsers block fetch() of local files
 *      from a file:// page), e.g. via `python3 -m http.server` in
 *      `src/`.
 */
async function loadPythonSource(inlineId, filename) {
    const inlineEl = document.getElementById(inlineId);
    if (inlineEl && inlineEl.textContent.trim().length > 0) {
        return inlineEl.textContent;
    }

    const response = await fetch(filename);
    if (!response.ok) {
        throw new Error(
            `Could not load ${filename} (HTTP ${response.status}). ` +
            "If you opened this file directly (file://), serve the " +
            "'src' folder via a local static server instead, e.g.:\n" +
            "  python3 -m http.server\n" +
            "...or run build.py to create a self-contained dist file."
        );
    }
    return await response.text();
}

async function main() {
    try {
        const pyodide = await loadPyodide();

        // Pure-Python "markdown" package for rendering the location /
        // detail descriptions (same library the Flask version used).
        await pyodide.loadPackage("micropip");
        const micropip = pyodide.pyimport("micropip");
        await micropip.install("markdown");

        const dataSource = await loadPythonSource("py-data", "data.py");
        const gameSource = await loadPythonSource("py-game", "game.py");

        pyodide.FS.writeFile("/data.py", dataSource);
        pyodide.FS.writeFile("/game.py", gameSource);

        pyodide.runPython("import sys; sys.path.insert(0, '/')");

        pyGame = pyodide.pyimport("game");

        renderApp();
        document.getElementById("loading").style.display = "none";
        document.getElementById("app").style.display = "block";
    } catch (err) {
        showError(err);
    }
}

main();
