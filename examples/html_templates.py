"""Inline HTML templates for the examples MCP demo server."""

MERMAID_VIEWER_TEMPLATE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Mermaid Diagram Viewer</title>
    <style>
      :root {
        color-scheme: light dark;
        --bg: #10141a;
        --panel: #151b22;
        --muted: #8da1b4;
        --text: #e5edf6;
        --accent: #4ea1ff;
        --border: #243242;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        font-family: Inter, system-ui, -apple-system, sans-serif;
        background: var(--bg);
        color: var(--text);
      }
      .layout {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
        min-height: 100vh;
        padding: 12px;
      }
      .panel {
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 10px;
        overflow: hidden;
      }
      .panel-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 10px 12px;
        border-bottom: 1px solid var(--border);
      }
      .toolbar {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      textarea {
        width: 100%;
        min-height: calc(100vh - 84px);
        border: 0;
        outline: none;
        resize: none;
        color: var(--text);
        background: transparent;
        padding: 12px;
        font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
        font-size: 13px;
        line-height: 1.5;
      }
      #preview {
        min-height: calc(100vh - 84px);
        padding: 12px;
        overflow: auto;
      }
      button, select {
        border: 1px solid var(--border);
        border-radius: 8px;
        background: #182331;
        color: var(--text);
        padding: 6px 10px;
      }
      button.primary {
        background: var(--accent);
        color: #081426;
        border: none;
        font-weight: 600;
      }
      .hint { color: var(--muted); font-size: 12px; }
      .fallback {
        border: 1px dashed #6b7f94;
        padding: 12px;
        border-radius: 8px;
        color: var(--muted);
      }
      @media (max-width: 920px) {
        .layout { grid-template-columns: 1fr; }
      }
    </style>
  </head>
  <body>
    <div class="layout">
      <section class="panel">
        <header class="panel-header">
          <strong>Mermaid Source</strong>
          <div class="toolbar">
            <select id="theme">
              {% for option in themes %}
              <option value="{{ option }}" {% if option == selected_theme %}selected{% endif %}>{{ option }}</option>
              {% endfor %}
            </select>
            <button id="render">Render</button>
            <button id="send" class="primary">Send to Chat</button>
          </div>
        </header>
        <textarea id="source">{{ initial_code }}</textarea>
      </section>
      <section class="panel">
        <header class="panel-header">
          <strong>Live Preview</strong>
          <span class="hint">Client re-render with Mermaid JS</span>
        </header>
        <div id="preview">
          {% if initial_svg %}
            {{ initial_svg | safe }}
          {% else %}
            <div class="fallback">
              Server-side <code>mermaid-cli</code> is unavailable. Use Render for client-side preview.
            </div>
          {% endif %}
        </div>
      </section>
    </div>

    <script type="module">
      import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";

      const bridge = window.__MCP_APPS_BRIDGE__ || {
        callServerTool(toolName, argumentsValue) {
          return new Promise((resolve) => {
            const id = "tool-" + Date.now();
            function onMessage(event) {
              if (event.data?.type === "response" && event.data?.id === id) {
                window.removeEventListener("message", onMessage);
                resolve(event.data.payload || {});
              }
            }
            window.addEventListener("message", onMessage);
            window.parent.postMessage({ type: "callServerTool", id, payload: { toolName, arguments: argumentsValue || {} } }, "*");
          });
        },
        sendMessage(role, content) {
          return new Promise((resolve) => {
            const id = "msg-" + Date.now();
            function onMessage(event) {
              if (event.data?.type === "response" && event.data?.id === id) {
                window.removeEventListener("message", onMessage);
                resolve(event.data.payload || {});
              }
            }
            window.addEventListener("message", onMessage);
            window.parent.postMessage({ type: "sendMessage", id, payload: { role, content } }, "*");
          });
        },
        updateModelContext(context) {
          return new Promise((resolve) => {
            const id = "ctx-" + Date.now();
            function onMessage(event) {
              if (event.data?.type === "response" && event.data?.id === id) {
                window.removeEventListener("message", onMessage);
                resolve(event.data.payload || {});
              }
            }
            window.addEventListener("message", onMessage);
            window.parent.postMessage({ type: "updateModelContext", id, payload: { context } }, "*");
          });
        }
      };
      try {
        const { App } = await import("https://esm.sh/@modelcontextprotocol/ext-apps");
        const app = new App();
        window.addEventListener("message", (event) => app.handleMessage(event));
      } catch (error) {
        console.debug("App class unavailable", error);
      }
      const sourceEl = document.getElementById("source");
      const previewEl = document.getElementById("preview");
      const renderBtn = document.getElementById("render");
      const sendBtn = document.getElementById("send");
      const themeEl = document.getElementById("theme");

      async function renderClient() {
        const code = sourceEl.value;
        const theme = themeEl.value;
        try {
          mermaid.initialize({ startOnLoad: false, securityLevel: "loose", theme });
          const id = "mermaid-" + Date.now();
          const result = await mermaid.render(id, code);
          previewEl.innerHTML = result.svg;
          if (bridge?.updateModelContext) {
            await bridge.updateModelContext({
              app: "mermaid-viewer",
              theme,
              lineCount: code.split("\\n").length
            });
          }
        } catch (error) {
          previewEl.innerHTML = '<div class="fallback">Render error: ' + error + "</div>";
        }
      }

      renderBtn.addEventListener("click", async () => {
        await renderClient();
      });

      sendBtn.addEventListener("click", async () => {
        if (!bridge?.sendMessage) return;
        await bridge.sendMessage(
          "user",
          "Please review this Mermaid diagram:\\n\\n```mermaid\\n" + sourceEl.value + "\\n```"
        );
      });

      themeEl.addEventListener("change", async () => {
        if (bridge?.callServerTool) {
          await bridge.callServerTool("render-mermaid", {
            code: sourceEl.value,
            theme: themeEl.value
          });
        }
        await renderClient();
      });
    </script>
  </body>
</html>
"""

SYSTEM_MONITOR_TEMPLATE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>System Monitor</title>
    <style>
      :root {
        --bg: #070b12;
        --panel: #111827;
        --line: #1f2a3a;
        --text: #dce9f8;
        --muted: #8ca0b8;
        --ok: #36c178;
        --warn: #f5b64c;
        --bad: #f97373;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        padding: 12px;
        font-family: Inter, system-ui, -apple-system, sans-serif;
        background: var(--bg);
        color: var(--text);
      }
      h1 { margin: 0 0 12px; font-size: 18px; }
      .grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(260px, 1fr));
        gap: 10px;
      }
      .card {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 10px;
        padding: 10px;
      }
      .kpi { font-size: 28px; margin: 8px 0; }
      .muted { color: var(--muted); font-size: 12px; }
      .bar {
        width: 100%;
        height: 12px;
        background: #0f1725;
        border-radius: 999px;
        overflow: hidden;
        border: 1px solid var(--line);
      }
      .fill {
        height: 100%;
        width: 0;
        background: linear-gradient(90deg, var(--ok), var(--warn), var(--bad));
      }
      table {
        width: 100%;
        border-collapse: collapse;
        font-size: 12px;
      }
      th, td {
        border-bottom: 1px solid var(--line);
        text-align: left;
        padding: 5px;
      }
      canvas { width: 100%; height: 130px; background: #0f1725; border-radius: 8px; }
      .controls {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 10px;
      }
      button, input {
        background: #1b2738;
        color: var(--text);
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 6px 8px;
      }
      @media (max-width: 900px) {
        .grid { grid-template-columns: 1fr; }
      }
    </style>
  </head>
  <body>
    <h1>Real-time System Monitor</h1>
    <div class="controls">
      <label class="muted">Interval (s)</label>
      <input id="interval" type="number" min="1" value="{{ interval }}" />
      <button id="refresh">Refresh</button>
      <span id="stamp" class="muted"></span>
    </div>

    <section class="grid">
      <article class="card">
        <div class="muted">CPU</div>
        <div id="cpuValue" class="kpi">0%</div>
        <div class="bar"><div id="cpuBar" class="fill"></div></div>
      </article>

      <article class="card">
        <div class="muted">Memory</div>
        <div id="memValue" class="kpi">0%</div>
        <div class="bar"><div id="memBar" class="fill"></div></div>
      </article>

      <article class="card">
        <div class="muted">Disk Usage</div>
        <canvas id="diskChart" width="560" height="130"></canvas>
      </article>

      <article class="card">
        <div class="muted">Top Processes</div>
        <table>
          <thead><tr><th>PID</th><th>Name</th><th>CPU %</th><th>Mem %</th></tr></thead>
          <tbody id="processRows"></tbody>
        </table>
      </article>
    </section>

    <script>
      const bridge = window.__MCP_APPS_BRIDGE__ || {
        callServerTool(toolName, argumentsValue) {
          return new Promise((resolve) => {
            const id = "tool-" + Date.now();
            function onMessage(event) {
              if (event.data?.type === "response" && event.data?.id === id) {
                window.removeEventListener("message", onMessage);
                resolve(event.data.payload || {});
              }
            }
            window.addEventListener("message", onMessage);
            window.parent.postMessage({ type: "callServerTool", id, payload: { toolName, arguments: argumentsValue || {} } }, "*");
          });
        },
        updateModelContext(context) {
          return new Promise((resolve) => {
            const id = "ctx-" + Date.now();
            function onMessage(event) {
              if (event.data?.type === "response" && event.data?.id === id) {
                window.removeEventListener("message", onMessage);
                resolve(event.data.payload || {});
              }
            }
            window.addEventListener("message", onMessage);
            window.parent.postMessage({ type: "updateModelContext", id, payload: { context } }, "*");
          });
        }
      };
      (async () => {
        try {
          const { App } = await import("https://esm.sh/@modelcontextprotocol/ext-apps");
          const app = new App();
          window.addEventListener("message", (event) => app.handleMessage(event));
        } catch (error) {
          console.debug("App class unavailable", error);
        }
      })();
      const cpuValue = document.getElementById("cpuValue");
      const memValue = document.getElementById("memValue");
      const cpuBar = document.getElementById("cpuBar");
      const memBar = document.getElementById("memBar");
      const processRows = document.getElementById("processRows");
      const diskCanvas = document.getElementById("diskChart");
      const stamp = document.getElementById("stamp");
      const refreshBtn = document.getElementById("refresh");
      const intervalEl = document.getElementById("interval");

      let diskHistory = [];
      let timer = null;
      const initialSnapshot = {{ snapshot_json | safe }};
      const selectedMetrics = {{ metrics_json | safe }};

      function fmt(value) {
        return Number(value || 0).toFixed(1);
      }

      function renderDiskChart(points) {
        const ctx = diskCanvas.getContext("2d");
        ctx.clearRect(0, 0, diskCanvas.width, diskCanvas.height);
        ctx.strokeStyle = "#5eb0ff";
        ctx.lineWidth = 2;
        ctx.beginPath();
        if (!points.length) return;
        const max = 100;
        const step = points.length > 1 ? (diskCanvas.width - 20) / (points.length - 1) : 0;
        points.forEach((point, index) => {
          const x = 10 + index * step;
          const y = 10 + (1 - point / max) * (diskCanvas.height - 20);
          if (index === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        });
        ctx.stroke();
      }

      function applySnapshot(snapshot) {
        const cpu = snapshot.cpu?.percent || 0;
        const mem = snapshot.memory?.percent || 0;
        const disk = snapshot.disk?.percent || 0;
        cpuValue.textContent = fmt(cpu) + "%";
        memValue.textContent = fmt(mem) + "%";
        cpuBar.style.width = cpu + "%";
        memBar.style.width = mem + "%";
        diskHistory.push(disk);
        if (diskHistory.length > 30) diskHistory = diskHistory.slice(-30);
        renderDiskChart(diskHistory);
        processRows.innerHTML = (snapshot.processes || []).map((proc) => (
          "<tr><td>" + proc.pid + "</td><td>" + proc.name + "</td><td>" +
          fmt(proc.cpu_percent) + "</td><td>" + fmt(proc.memory_percent) + "</td></tr>"
        )).join("");
        stamp.textContent = "Updated " + new Date().toLocaleTimeString();
      }

      async function pollSnapshot() {
        if (!bridge?.callServerTool) return;
        const response = await bridge.callServerTool("get-snapshot", { metrics: selectedMetrics });
        const payload = response?.result?.snapshot || response?.snapshot || response;
        applySnapshot(payload);
        if (bridge?.updateModelContext) {
          await bridge.updateModelContext({
            app: "system-monitor",
            cpu: payload.cpu?.percent,
            memory: payload.memory?.percent,
            disk: payload.disk?.percent
          });
        }
      }

      function restartPolling() {
        if (timer) clearInterval(timer);
        const interval = Math.max(1, Number(intervalEl.value || 5)) * 1000;
        timer = setInterval(() => {
          pollSnapshot().catch((error) => console.error(error));
        }, interval);
      }

      refreshBtn.addEventListener("click", async () => {
        await pollSnapshot();
        restartPolling();
      });

      applySnapshot(initialSnapshot);
      restartPolling();
    </script>
  </body>
</html>
"""

DATA_TABLE_TEMPLATE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Interactive Data Table</title>
    <style>
      :root {
        --bg: #0e1117;
        --panel: #161b22;
        --line: #2b3340;
        --text: #d6e2f0;
        --muted: #8ea2ba;
        --accent: #4ea1ff;
      }
      body {
        margin: 0;
        padding: 14px;
        font-family: Inter, system-ui, -apple-system, sans-serif;
        background: var(--bg);
        color: var(--text);
      }
      .controls {
        display: grid;
        grid-template-columns: 1fr auto auto auto;
        gap: 8px;
        margin-bottom: 10px;
      }
      textarea, input, button {
        background: #111826;
        color: var(--text);
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 8px;
      }
      textarea {
        min-height: 80px;
        font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      }
      button.primary {
        border: none;
        background: var(--accent);
        color: #0b1626;
        font-weight: 700;
      }
      .table-wrap {
        border: 1px solid var(--line);
        border-radius: 10px;
        overflow: auto;
        resize: both;
        min-height: 280px;
      }
      table {
        width: 100%;
        border-collapse: collapse;
        min-width: 760px;
      }
      th, td {
        border-bottom: 1px solid var(--line);
        padding: 8px;
        font-size: 13px;
        white-space: nowrap;
      }
      th {
        position: sticky;
        top: 0;
        background: #1a2334;
        cursor: col-resize;
      }
      .muted { color: var(--muted); font-size: 12px; margin-top: 8px; }
    </style>
  </head>
  <body>
    <div class="controls">
      <textarea id="sql">{{ query }}</textarea>
      <input id="limit" type="number" value="{{ limit }}" min="1" />
      <button id="run">Run Query</button>
      <button id="analyze" class="primary">Analyze</button>
    </div>
    <div class="controls">
      <input id="filter" placeholder="Filter rows" />
      <button id="export">Export CSV</button>
      <div></div>
      <div></div>
    </div>
    <div class="table-wrap">
      <table id="dataTable"></table>
    </div>
    <div id="status" class="muted"></div>

    <script>
      const bridge = window.__MCP_APPS_BRIDGE__ || {
        callServerTool(toolName, argumentsValue) {
          return new Promise((resolve) => {
            const id = "tool-" + Date.now();
            function onMessage(event) {
              if (event.data?.type === "response" && event.data?.id === id) {
                window.removeEventListener("message", onMessage);
                resolve(event.data.payload || {});
              }
            }
            window.addEventListener("message", onMessage);
            window.parent.postMessage({ type: "callServerTool", id, payload: { toolName, arguments: argumentsValue || {} } }, "*");
          });
        },
        sendMessage(role, content) {
          return new Promise((resolve) => {
            const id = "msg-" + Date.now();
            function onMessage(event) {
              if (event.data?.type === "response" && event.data?.id === id) {
                window.removeEventListener("message", onMessage);
                resolve(event.data.payload || {});
              }
            }
            window.addEventListener("message", onMessage);
            window.parent.postMessage({ type: "sendMessage", id, payload: { role, content } }, "*");
          });
        },
        updateModelContext(context) {
          return new Promise((resolve) => {
            const id = "ctx-" + Date.now();
            function onMessage(event) {
              if (event.data?.type === "response" && event.data?.id === id) {
                window.removeEventListener("message", onMessage);
                resolve(event.data.payload || {});
              }
            }
            window.addEventListener("message", onMessage);
            window.parent.postMessage({ type: "updateModelContext", id, payload: { context } }, "*");
          });
        }
      };
      (async () => {
        try {
          const { App } = await import("https://esm.sh/@modelcontextprotocol/ext-apps");
          const app = new App();
          window.addEventListener("message", (event) => app.handleMessage(event));
        } catch (error) {
          console.debug("App class unavailable", error);
        }
      })();
      const sqlEl = document.getElementById("sql");
      const runBtn = document.getElementById("run");
      const exportBtn = document.getElementById("export");
      const analyzeBtn = document.getElementById("analyze");
      const limitEl = document.getElementById("limit");
      const filterEl = document.getElementById("filter");
      const tableEl = document.getElementById("dataTable");
      const statusEl = document.getElementById("status");

      let columns = {{ columns_json | safe }};
      let rows = {{ rows_json | safe }};
      let sortState = { key: null, dir: 1 };

      function renderTable(sourceRows) {
        const filtered = sourceRows.filter((row) => {
          const needle = filterEl.value.trim().toLowerCase();
          if (!needle) return true;
          return Object.values(row).some((value) => String(value).toLowerCase().includes(needle));
        });

        const header = "<thead><tr>" + columns.map((col) =>
          "<th data-col='" + col + "'>" + col + "</th>"
        ).join("") + "</tr></thead>";
        const body = "<tbody>" + filtered.map((row) =>
          "<tr>" + columns.map((col) => "<td>" + (row[col] ?? "") + "</td>").join("") + "</tr>"
        ).join("") + "</tbody>";

        tableEl.innerHTML = header + body;
        statusEl.textContent = filtered.length + " rows";

        tableEl.querySelectorAll("th").forEach((th) => {
          th.addEventListener("click", () => {
            const key = th.dataset.col;
            if (!key) return;
            sortState.dir = sortState.key === key ? -sortState.dir : 1;
            sortState.key = key;
            rows = [...rows].sort((a, b) => {
              const av = a[key];
              const bv = b[key];
              if (av === bv) return 0;
              return av > bv ? sortState.dir : -sortState.dir;
            });
            renderTable(rows);
          });
        });
        enableColumnResize();
      }

      function enableColumnResize() {
        tableEl.querySelectorAll("th").forEach((th) => {
          let startX = 0;
          let startWidth = 0;
          function onMove(event) {
            const width = Math.max(80, startWidth + (event.clientX - startX));
            th.style.width = width + "px";
          }
          function onUp() {
            window.removeEventListener("mousemove", onMove);
            window.removeEventListener("mouseup", onUp);
          }
          th.addEventListener("mousedown", (event) => {
            startX = event.clientX;
            startWidth = th.getBoundingClientRect().width;
            window.addEventListener("mousemove", onMove);
            window.addEventListener("mouseup", onUp);
          });
        });
      }

      async function runQuery() {
        if (!bridge?.callServerTool) return;
        const response = await bridge.callServerTool("query-table", {
          query: sqlEl.value,
          limit: Number(limitEl.value || 20)
        });
        const payload = response?.result || response;
        columns = payload.columns || [];
        rows = payload.rows || [];
        renderTable(rows);
        if (bridge?.updateModelContext) {
          await bridge.updateModelContext({
            app: "data-table",
            rowCount: rows.length,
            columns
          });
        }
      }

      runBtn.addEventListener("click", () => runQuery().catch((error) => {
        statusEl.textContent = "Query error: " + error;
      }));
      filterEl.addEventListener("input", () => renderTable(rows));

      exportBtn.addEventListener("click", async () => {
        if (!bridge?.callServerTool) return;
        const response = await bridge.callServerTool("export-csv", {
          query: sqlEl.value,
          limit: Number(limitEl.value || 20)
        });
        const payload = response?.result || response;
        const blob = new Blob([payload.csv || ""], { type: "text/csv;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = payload.filename || "export.csv";
        a.click();
        URL.revokeObjectURL(url);
      });

      analyzeBtn.addEventListener("click", async () => {
        if (!bridge?.sendMessage) return;
        await bridge.sendMessage(
          "user",
          "Analyze this SQL result set. Query: " + sqlEl.value + " | Rows: " + rows.length
        );
      });

      renderTable(rows);
    </script>
  </body>
</html>
"""
