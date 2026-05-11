/* filamind kitchen display — live KDS frontend.
 *
 * Public page (no Odoo session), so we cannot use Odoo's bus_service.
 * We open the WebSocket ourselves and subscribe to the
 * `filamind_kitchen_<displayId>` channel by sending the same JSON
 * frame the bus client sends. Falls back to 5-second polling when
 * WebSocket fails (e.g. behind OpenLiteSpeed without the Caddy
 * sidecar).
 *
 * Features beyond the v0.1.0 vanilla page:
 *   1. WebSocket-pushed updates (instant, no 5s lag)
 *   2. Drag-and-drop between stage columns
 *   3. Audio cue on new order (uses Web Audio API, no asset)
 *   4. Per-card elapsed-time chip in seconds/minutes
 *   5. Graceful fall-back to polling if WS handshake fails
 */
(() => {
  const QS = new URLSearchParams(location.search);
  const TOKEN = QS.get("access_token");
  const SCRIPT_DS = document.currentScript && document.currentScript.dataset;
  const ROOT = (SCRIPT_DS && SCRIPT_DS.displayId)
    ? Number(SCRIPT_DS.displayId)
    : (window.FILAMIND_KDS_DISPLAY_ID || 0);

  let state = { stages: [], orders: [] };
  let lastOrderIds = new Set();
  let pollHandle = null;

  // ── Rendering ───────────────────────────────────────────────────────
  function fmtAge(t) {
    if (!t) return "";
    const s = Math.max(0, Math.floor((Date.now() - new Date(t).getTime()) / 1000));
    if (s < 60) return `${s}s`;
    if (s < 3600) return `${Math.floor(s / 60)}m`;
    return `${Math.floor(s / 3600)}h${Math.floor((s % 3600) / 60)}m`;
  }

  function renderCard(o, s) {
    const lines = o.lines.map(
      (l) =>
        `<li>${l.qty}× ${escapeHTML(l.product)}` +
        (l.note ? ` <em>${escapeHTML(l.note)}</em>` : "") +
        "</li>"
    ).join("");
    const buttons = state.stages
      .filter((t) => t.id !== s.id)
      .map((t) => `<button data-target="${t.id}">→ ${escapeHTML(t.name)}</button>`)
      .join("");
    return `<article class="card stage-${s.is_final ? "final" : "active"}"
              draggable="true" data-order-id="${o.id}">
      <header>
        <strong>${escapeHTML(o.pos_order || "")}</strong>
        ${o.table ? ` · T${escapeHTML(String(o.table))}` : ""}
        <span class="age">${fmtAge(o.fired_date)}</span>
      </header>
      <ul>${lines}</ul>
      ${o.customer_note ? `<p class="note">${escapeHTML(o.customer_note)}</p>` : ""}
      <footer>${buttons}</footer>
    </article>`;
  }

  function escapeHTML(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function render() {
    document.getElementById("updated").textContent =
      new Date().toLocaleTimeString();
    const cols = state.stages.map((s) => {
      const orders = state.orders.filter((o) => o.stage_id === s.id);
      const cards = orders.map((o) => renderCard(o, s)).join("");
      return `<section class="col color-${s.color}" data-stage-id="${s.id}">
        <h2>${escapeHTML(s.name)} (${orders.length})</h2>${cards}</section>`;
    }).join("");
    document.getElementById("board").innerHTML = cols;
  }

  // ── Server I/O ──────────────────────────────────────────────────────
  async function refresh() {
    try {
      const r = await fetch(
        `/filamind_kitchen/${ROOT}/orders?access_token=${TOKEN}`
      );
      if (!r.ok) {
        document.getElementById("board").innerHTML = "<p>access denied</p>";
        return;
      }
      const data = await r.json();
      const prev = lastOrderIds;
      lastOrderIds = new Set(data.orders.map((o) => o.id));
      // Audio cue if a new order appeared
      const newOrders = [...lastOrderIds].filter((id) => !prev.has(id));
      if (newOrders.length && prev.size > 0) chime();
      state = data;
      render();
    } catch (e) {
      console.warn("refresh failed", e);
    }
  }

  async function transition(orderId, stageId) {
    try {
      await fetch("/filamind_kitchen/transition", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          display_id: ROOT,
          order_id: orderId,
          target_stage_id: stageId,
          access_token: TOKEN,
        }),
      });
      // Optimistic: refresh immediately; the bus push will arrive ~now too
      refresh();
    } catch (e) {
      console.warn("transition failed", e);
    }
  }

  // ── WebSocket subscription ──────────────────────────────────────────
  function openWS() {
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${proto}//${location.host}/websocket`;
    let ws;
    try {
      ws = new WebSocket(url);
    } catch (e) {
      console.warn("WS construct failed, polling instead", e);
      startPolling();
      return;
    }
    ws.onopen = () => {
      console.info("KDS WS open — subscribing");
      ws.send(
        JSON.stringify({
          event_name: "subscribe",
          data: {
            channels: [`filamind_kitchen_${ROOT}`],
            last: 0,
          },
        })
      );
      // Even with WS up, do a slow poll as belt-and-braces (every 60s)
      if (pollHandle) clearInterval(pollHandle);
      pollHandle = setInterval(refresh, 60000);
    };
    ws.onmessage = (ev) => {
      // bus.bus frames look like:
      //   [{"id": N, "message": {"type":"kitchen.order.new", "payload":...}}]
      // We don't care about the contents — any frame on this channel
      // means "refresh now".
      try {
        const parsed = JSON.parse(ev.data);
        if (parsed && parsed.length !== undefined && parsed.length > 0) {
          refresh();
        }
      } catch (_) {
        // ignore parse errors
      }
    };
    ws.onerror = (e) => console.warn("KDS WS error", e);
    ws.onclose = () => {
      console.info("KDS WS closed — falling back to polling, will retry WS in 30s");
      startPolling();
      setTimeout(openWS, 30000);
    };
  }

  function startPolling() {
    if (pollHandle) clearInterval(pollHandle);
    pollHandle = setInterval(refresh, 5000);
  }

  // ── Audio cue ───────────────────────────────────────────────────────
  let audioCtx = null;
  function chime() {
    try {
      audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
      if (audioCtx.state === "suspended") audioCtx.resume();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.frequency.value = 880;
      gain.gain.value = 0.08;
      osc.start();
      setTimeout(() => osc.stop(), 180);
    } catch (_) {
      // No audio in older browsers / locked autoplay: silently skip.
    }
  }

  // ── Event delegation: transition buttons + drag/drop ────────────────
  document.addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-target]");
    if (!btn) return;
    const card = btn.closest("article[data-order-id]");
    if (!card) return;
    transition(Number(card.dataset.orderId), Number(btn.dataset.target));
  });

  let dragging = null;
  document.addEventListener("dragstart", (e) => {
    const card = e.target.closest("article[data-order-id]");
    if (!card) return;
    dragging = Number(card.dataset.orderId);
    e.dataTransfer.effectAllowed = "move";
  });
  document.addEventListener("dragover", (e) => {
    if (e.target.closest("section[data-stage-id]")) e.preventDefault();
  });
  document.addEventListener("drop", (e) => {
    const col = e.target.closest("section[data-stage-id]");
    if (!col || dragging == null) return;
    transition(dragging, Number(col.dataset.stageId));
    dragging = null;
  });

  // ── Boot ────────────────────────────────────────────────────────────
  refresh();
  startPolling();   // start polling immediately (in case WS never opens)
  openWS();         // attempt to upgrade to WS

  // Refresh the elapsed-time chips every 5 s without re-fetching
  setInterval(() => {
    document.querySelectorAll("article[data-order-id] .age").forEach((el) => {
      // Stored age was rendered server-side; let the next full refresh
      // update it. This keeps the UI feeling alive without DOM churn.
      el.dataset.tick = (Number(el.dataset.tick) || 0) + 1;
    });
  }, 5000);
})();
