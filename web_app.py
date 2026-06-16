from flask import Flask, render_template_string, request, jsonify
import asyncio
import os
import uuid
import json
import threading
import time as time_mod
from datetime import datetime, time
from werkzeug.utils import secure_filename

from idotmatrix import Clock, Gif, Image, ConnectionManager

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
SCHEDULE_FILE = os.path.join(BASE_DIR, "schedule.json")
STATE_FILE = os.path.join(BASE_DIR, "state.json")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

DAYS_PT = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"]


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def load_schedule() -> list:
    if not os.path.exists(SCHEDULE_FILE):
        return []
    with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_schedule(items: list) -> None:
    with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)


def load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {"enabled": False, "current_item": None, "phase": "idle"}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def time_str_to_tuple(s: str) -> time:
    h, m = s.split(":")
    return time(int(h), int(m))


def item_active_now(item: dict, now: datetime) -> bool:
    weekday = now.weekday()
    day_key = DAYS_PT[weekday]
    if day_key not in item.get("days", []):
        return False
    start = time_str_to_tuple(item["start_time"])
    end = time_str_to_tuple(item["end_time"])
    t = now.time()
    if start <= end:
        return start <= t < end
    return t >= start or t < end


def find_active_item() -> dict | None:
    now = datetime.now()
    for item in load_schedule():
        if item.get("enabled", True) and item_active_now(item, now):
            return item
    return None


async def _connect(address: str | None) -> tuple[bool, str | None, str | None]:
    conn = ConnectionManager()
    try:
        if address:
            await conn.connectByAddress(address)
        else:
            await conn.connectBySearch()
        if conn.client and conn.client.is_connected:
            return True, conn.address, None
        return False, None, "N\u00e3o foi poss\u00edvel conectar ao dispositivo"
    except Exception as e:
        return False, None, str(e)


async def _set_clock(style, hour24, visible_date, r, g, b):
    clock = Clock()
    await clock.setMode(style=style, hour24=hour24, visibleDate=visible_date, r=r, g=g, b=b)


async def _enter_diy():
    image = Image()
    await image.setMode(1)


async def _send_gif(file_path: str, pixel_size: int):
    gif = Gif()
    await gif.uploadProcessed(file_path, pixel_size=pixel_size)


async def _run_phase(item: dict, phase: str, pixel_size: int):
    if phase == "gif":
        await _enter_diy()
        await _send_gif(item["gif_path"], pixel_size)
    elif phase == "clock":
        await _set_clock(
            style=item.get("clock_style", 4),
            hour24=item.get("hour24", True),
            visible_date=item.get("visibleDate", True),
            r=item.get("r", 255),
            g=item.get("g", 255),
            b=item.get("b", 255),
        )


class Scheduler:
    def __init__(self):
        self._stop = threading.Event()
        self.thread: threading.Thread | None = None

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self._stop.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self._stop.set()

    def _run(self):
        last_item_id = None
        phase = "gif"
        phase_started = 0.0
        while not self._stop.is_set():
            state = load_state()
            if not state.get("enabled", False):
                last_item_id = None
                phase = "gif"
                time_mod.sleep(1)
                continue

            item = find_active_item()
            if not item:
                last_item_id = None
                state["current_item"] = None
                state["phase"] = "idle"
                save_state(state)
                time_mod.sleep(2)
                continue

            pixel_size = int(state.get("pixels", 32))

            if item["id"] != last_item_id:
                last_item_id = item["id"]
                phase = "gif"
                phase_started = time_mod.time()
                state["current_item"] = item["id"]
                state["phase"] = "gif"
                save_state(state)
                try:
                    run_async(_run_phase(item, "gif", pixel_size))
                except Exception as e:
                    print(f"[scheduler] error in gif phase: {e}")
                continue

            now = time_mod.time()
            elapsed = now - phase_started
            if phase == "gif" and elapsed >= item.get("gif_seconds", 10):
                phase = "clock"
                phase_started = now
                state["phase"] = "clock"
                save_state(state)
                try:
                    run_async(_run_phase(item, "clock", pixel_size))
                except Exception as e:
                    print(f"[scheduler] error in clock phase: {e}")
            elif phase == "clock" and elapsed >= item.get("clock_seconds", 12):
                phase = "gif"
                phase_started = now
                state["phase"] = "gif"
                save_state(state)
                try:
                    run_async(_run_phase(item, "gif", pixel_size))
                except Exception as e:
                    print(f"[scheduler] error in gif phase: {e}")

            time_mod.sleep(1)


scheduler = Scheduler()
scheduler.start()


HTML = """
<!doctype html>
<html lang="pt-br">
<head>
    <meta charset="utf-8">
    <title>iDotMatrix Web</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        :root {
            --bg: #0f172a;
            --card: #1e293b;
            --accent: #38bdf8;
            --accent-hover: #0ea5e9;
            --text: #e2e8f0;
            --muted: #94a3b8;
            --success: #22c55e;
            --error: #ef4444;
        }
        * { box-sizing: border-box; }
        body {
            font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 2rem 1rem;
            min-height: 100vh;
        }
        .container { max-width: 820px; margin: 0 auto; }
        h1 { text-align: center; margin-bottom: 0.25rem; }
        .subtitle { text-align: center; color: var(--muted); margin-top: 0; margin-bottom: 2rem; }
        .card {
            background: var(--card);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.25rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.25);
        }
        .card h2 { margin-top: 0; font-size: 1.15rem; }
        label { display: block; margin: 0.5rem 0 0.25rem; color: var(--muted); font-size: 0.9rem; }
        input[type=text], input[type=time], input[type=file], input[type=number], select {
            width: 100%;
            padding: 0.55rem;
            border-radius: 8px;
            border: 1px solid #334155;
            background: #0f172a;
            color: var(--text);
            margin-bottom: 0.5rem;
        }
        button {
            background: var(--accent);
            color: #0f172a;
            border: 0;
            border-radius: 8px;
            padding: 0.6rem 1.1rem;
            font-weight: 600;
            cursor: pointer;
            font-size: 0.9rem;
            transition: background 0.15s;
        }
        button:hover { background: var(--accent-hover); }
        button.secondary { background: #475569; color: var(--text); }
        button.secondary:hover { background: #334155; }
        button.danger { background: #ef4444; color: #fff; }
        button.danger:hover { background: #dc2626; }
        .row { display: flex; gap: 0.75rem; flex-wrap: wrap; align-items: end; }
        .row > div { flex: 1 1 120px; }
        .status {
            margin-top: 1rem;
            padding: 0.75rem;
            border-radius: 8px;
            font-size: 0.9rem;
            display: none;
        }
        .status.ok { display: block; background: rgba(34,197,94,0.15); color: var(--success); }
        .status.err { display: block; background: rgba(239,68,68,0.15); color: var(--error); }
        .color-row { display: flex; gap: 0.5rem; }
        .color-row input { width: 100%; }
        .display-pill {
            display: inline-block;
            background: rgba(56,189,248,0.15);
            color: var(--accent);
            padding: 0.25rem 0.6rem;
            border-radius: 999px;
            font-size: 0.85rem;
            font-weight: 600;
        }
        .days { display: flex; gap: 0.4rem; flex-wrap: wrap; }
        .days label {
            display: inline-flex;
            align-items: center;
            gap: 0.3rem;
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 0.4rem 0.7rem;
            margin: 0;
            color: var(--text);
            cursor: pointer;
            font-size: 0.85rem;
        }
        .days input { margin: 0; }
        .schedule-item {
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 10px;
            padding: 0.9rem 1rem;
            margin-bottom: 0.6rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 0.75rem;
            flex-wrap: wrap;
        }
        .schedule-item .info { flex: 1 1 200px; }
        .schedule-item .info strong { display: block; margin-bottom: 0.25rem; }
        .schedule-item .info small { color: var(--muted); }
        .schedule-item .actions { display: flex; gap: 0.4rem; }
        .live-status {
            margin-top: 1rem;
            padding: 0.75rem 1rem;
            background: rgba(56,189,248,0.1);
            border-left: 3px solid var(--accent);
            border-radius: 6px;
            font-size: 0.9rem;
        }
        .live-status strong { color: var(--accent); }
        .toggle-btn {
            background: #475569;
            color: var(--text);
            border: 0;
            border-radius: 8px;
            padding: 0.7rem 1.2rem;
            font-weight: 600;
            cursor: pointer;
        }
        .toggle-btn.on { background: var(--success); color: #0f172a; }
    </style>
</head>
<body>
<div class="container">
    <h1>iDotMatrix Web</h1>
    <p class="subtitle">Controle seu display LED pelo navegador</p>

    <div class="card">
        <h2>1. Conex&atilde;o &amp; Display</h2>
        <div class="row">
            <div style="flex: 2 1 200px;">
                <label>Endere&ccedil;o Bluetooth (opcional)</label>
                <input type="text" id="btAddress" placeholder="ex.: AA:BB:CC:DD:EE:FF">
            </div>
            <div>
                <label>Tamanho do display</label>
                <select id="displayPixels">
                    <option value="16">16x16</option>
                    <option value="32" selected>32x32</option>
                    <option value="64">64x64</option>
                </select>
            </div>
            <div>
                <button id="btnConnect">Conectar</button>
            </div>
            <div>
                <button id="btnDisconnect" class="secondary" disabled>Desconectar</button>
            </div>
        </div>
        <p style="margin: 0.5rem 0 0; font-size: 0.85rem; color: var(--muted);">
            Tamanho atual: <span class="display-pill" id="displayPill">32x32</span>
            &middot; Status: <span id="connPill" class="display-pill" style="background: rgba(239,68,68,0.15); color: var(--error);">desconectado</span>
        </p>
        <div id="connStatus" class="status"></div>
    </div>

    <div class="card" id="card-clock">
        <h2>2. Rel&oacute;gio (manual)</h2>
        <div class="row">
            <div>
                <label>Estilo (0-7)</label>
                <input type="number" id="clockStyle" min="0" max="7" value="4">
            </div>
            <div>
                <label>Formato</label>
                <select id="clock24">
                    <option value="1" selected>24h</option>
                    <option value="0">12h</option>
                </select>
            </div>
            <div>
                <label>Mostrar data</label>
                <select id="clockDate">
                    <option value="1" selected>Sim</option>
                    <option value="0">N&atilde;o</option>
                </select>
            </div>
        </div>
        <div class="row">
            <div style="flex: 2 1 200px;">
                <label>Cor (R G B)</label>
                <div class="color-row">
                    <input type="number" id="clockR" min="0" max="255" value="255">
                    <input type="number" id="clockG" min="0" max="255" value="255">
                    <input type="number" id="clockB" min="0" max="255" value="255">
                </div>
            </div>
            <div>
                <button id="btnClock" disabled>Ativar rel&oacute;gio</button>
            </div>
        </div>
        <div id="clockStatus" class="status"></div>
    </div>

    <div class="card" id="card-gif">
        <h2>3. GIF avulso</h2>
        <form id="gifForm" enctype="multipart/form-data">
            <div class="row">
                <div style="flex: 3 1 250px;">
                    <label>Arquivo .gif</label>
                    <input type="file" id="gifFile" accept="image/gif,.gif" required>
                </div>
                <div>
                    <button id="btnGif" type="submit" disabled>Enviar GIF</button>
                </div>
            </div>
        </form>
        <div id="gifStatus" class="status"></div>
    </div>

    <div class="card" id="card-schedule">
        <h2>4. Agendamento de GIFs</h2>
        <p style="margin: 0 0 0.75rem; color: var(--muted); font-size: 0.9rem;">
            Programe GIFs por dia da semana e hor&aacute;rio. A cada <em>X</em> segundos de GIF, mostra o rel&oacute;gio por <em>Y</em> segundos, intercalando.
        </p>
        <div class="row">
            <div>
                <button id="btnToggleScheduler" class="toggle-btn" disabled>Agendamento: OFF</button>
            </div>
            <div style="flex: 2 1 200px;">
                <div class="live-status" id="liveStatus">Aguardando...</div>
            </div>
        </div>

        <h3 style="margin-top: 1.5rem; font-size: 1rem;">Novo agendamento</h3>
        <form id="scheduleForm" enctype="multipart/form-data">
            <div class="row">
                <div style="flex: 2 1 200px;">
                    <label>Arquivo .gif</label>
                    <input type="file" id="schedGifFile" accept="image/gif,.gif" required>
                </div>
                <div>
                    <label>In&iacute;cio</label>
                    <input type="time" id="schedStart" value="08:00" required>
                </div>
                <div>
                    <label>Fim</label>
                    <input type="time" id="schedEnd" value="18:00" required>
                </div>
            </div>
            <div class="row">
                <div>
                    <label>Segundos de GIF</label>
                    <input type="number" id="schedGifSec" min="1" value="10">
                </div>
                <div>
                    <label>Segundos de rel&oacute;gio</label>
                    <input type="number" id="schedClockSec" min="1" value="12">
                </div>
                <div>
                    <label>Estilo rel&oacute;gio (0-7)</label>
                    <input type="number" id="schedClockStyle" min="0" max="7" value="4">
                </div>
            </div>
            <div class="row">
                <div>
                    <label>Formato</label>
                    <select id="schedClock24">
                        <option value="1" selected>24h</option>
                        <option value="0">12h</option>
                    </select>
                </div>
                <div>
                    <label>Mostrar data</label>
                    <select id="schedClockDate">
                        <option value="1" selected>Sim</option>
                        <option value="0">N&atilde;o</option>
                    </select>
                </div>
                <div style="flex: 2 1 200px;">
                    <label>Cor (R G B)</label>
                    <div class="color-row">
                        <input type="number" id="schedR" min="0" max="255" value="255">
                        <input type="number" id="schedG" min="0" max="255" value="255">
                        <input type="number" id="schedB" min="0" max="255" value="255">
                    </div>
                </div>
            </div>
            <div>
                <label>Dias da semana</label>
                <div class="days" id="daysContainer">
                    <label><input type="checkbox" value="seg" checked> Seg</label>
                    <label><input type="checkbox" value="ter" checked> Ter</label>
                    <label><input type="checkbox" value="qua" checked> Qua</label>
                    <label><input type="checkbox" value="qui" checked> Qui</label>
                    <label><input type="checkbox" value="sex" checked> Sex</label>
                    <label><input type="checkbox" value="sab"> S&aacute;b</label>
                    <label><input type="checkbox" value="dom"> Dom</label>
                </div>
            </div>
            <div style="margin-top: 0.75rem;">
                <button id="btnAddSchedule" type="submit" disabled>Adicionar agendamento</button>
            </div>
        </form>
        <div id="scheduleStatus" class="status"></div>

        <h3 style="margin-top: 1.5rem; font-size: 1rem;">Agendamentos</h3>
        <div id="scheduleList"></div>
    </div>

</div>

<script>
function setStatus(el, ok, msg) {
    el.className = "status " + (ok ? "ok" : "err");
    el.textContent = msg;
}
function clearStatus(el) {
    el.className = "status";
    el.textContent = "";
}

async function postJSON(url, payload) {
    const r = await fetch(url, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload),
    });
    return r.json();
}

const btnConnect = document.getElementById("btnConnect");
const btnDisconnect = document.getElementById("btnDisconnect");
const btnClock = document.getElementById("btnClock");
const btnGif = document.getElementById("btnGif");
const btnToggleScheduler = document.getElementById("btnToggleScheduler");
const btnAddSchedule = document.getElementById("btnAddSchedule");
const connPill = document.getElementById("connPill");

let isConnected = false;

function setConnected(connected) {
    isConnected = connected;
    btnConnect.disabled = connected;
    btnDisconnect.disabled = !connected;
    btnClock.disabled = !connected;
    btnGif.disabled = !connected;
    btnAddSchedule.disabled = !connected;
    updateSchedulerBtn();
    if (connected) {
        connPill.textContent = "conectado";
        connPill.style.background = "rgba(34,197,94,0.15)";
        connPill.style.color = "var(--success)";
    } else {
        connPill.textContent = "desconectado";
        connPill.style.background = "rgba(239,68,68,0.15)";
        connPill.style.color = "var(--error)";
    }
}

function updateSchedulerBtn() {
    btnToggleScheduler.disabled = !isConnected;
}

const pixelsSel = document.getElementById("displayPixels");
const pill = document.getElementById("displayPill");
const savedPixels = localStorage.getItem("idotmatrix_pixels");
if (savedPixels && ["16", "32", "64"].includes(savedPixels)) {
    pixelsSel.value = savedPixels;
}
function updatePill() {
    pill.textContent = pixelsSel.value + "x" + pixelsSel.value;
    localStorage.setItem("idotmatrix_pixels", pixelsSel.value);
}
updatePill();
pixelsSel.addEventListener("change", updatePill);

document.getElementById("btnConnect").onclick = async () => {
    const addr = document.getElementById("btAddress").value.trim();
    const status = document.getElementById("connStatus");
    status.className = "status";
    status.textContent = "Conectando...";
    status.style.display = "block";
    btnConnect.disabled = true;
    btnDisconnect.disabled = true;
    try {
        const data = await postJSON("/connect", {address: addr || null});
        setStatus(status, data.ok, data.ok ? "Conectado a " + data.address : "Erro: " + data.error);
        setConnected(data.ok);
    } catch (e) {
        setStatus(status, false, "Erro: " + e);
        setConnected(false);
    }
};

document.getElementById("btnDisconnect").onclick = async () => {
    const status = document.getElementById("connStatus");
    try {
        const data = await postJSON("/disconnect", {});
        setStatus(status, data.ok, data.ok ? "Desconectado." : "Erro: " + data.error);
    } catch (e) {
        setStatus(status, false, "Erro: " + e);
    }
    setConnected(false);
};

document.getElementById("btnClock").onclick = async () => {
    const status = document.getElementById("clockStatus");
    const other = document.getElementById("gifStatus");
    const payload = {
        style: parseInt(document.getElementById("clockStyle").value),
        hour24: document.getElementById("clock24").value === "1",
        visibleDate: document.getElementById("clockDate").value === "1",
        r: parseInt(document.getElementById("clockR").value),
        g: parseInt(document.getElementById("clockG").value),
        b: parseInt(document.getElementById("clockB").value),
    };
    clearStatus(other);
    status.className = "status";
    status.textContent = "Enviando comando...";
    status.style.display = "block";
    try {
        const data = await postJSON("/clock", payload);
        setStatus(status, data.ok, data.ok ? "Rel&oacute;gio ativado!" : "Erro: " + data.error);
    } catch (e) {
        setStatus(status, false, "Erro: " + e);
    }
};

document.getElementById("gifForm").onsubmit = async (e) => {
    e.preventDefault();
    const status = document.getElementById("gifStatus");
    const other = document.getElementById("clockStatus");
    const fileInput = document.getElementById("gifFile");
    if (!fileInput.files.length) return;
    const form = new FormData();
    form.append("file", fileInput.files[0]);
    form.append("pixels", pixelsSel.value);
    clearStatus(other);
    status.className = "status";
    status.textContent = "Enviando GIF...";
    status.style.display = "block";
    try {
        const r = await fetch("/gif", {method: "POST", body: form});
        const data = await r.json();
        setStatus(status, data.ok, data.ok ? "GIF enviado!" : "Erro: " + data.error);
    } catch (err) {
        setStatus(status, false, "Erro: " + err);
    }
};

const schedStatus = document.getElementById("scheduleStatus");
const schedList = document.getElementById("scheduleList");
const liveStatus = document.getElementById("liveStatus");
const btnToggle = document.getElementById("btnToggleScheduler");

async function refreshSchedule() {
    const r = await fetch("/schedule");
    const data = await r.json();
    const items = data.items || [];
    if (items.length === 0) {
        schedList.innerHTML = '<p style="color: var(--muted); font-size: 0.9rem;">Nenhum agendamento.</p>';
        return;
    }
    schedList.innerHTML = items.map(it => {
        const days = (it.days || []).join(", ");
        return `
        <div class="schedule-item" data-id="${it.id}">
            <div class="info">
                <strong>${it.gif_name || '(gif)'}</strong>
                <small>${it.start_time} - ${it.end_time} &middot; ${days}</small><br>
                <small>GIF ${it.gif_seconds}s &rarr; rel&oacute;gio ${it.clock_seconds}s &middot; estilo ${it.clock_style}</small>
            </div>
            <div class="actions">
                <button class="secondary" onclick="toggleItem('${it.id}', ${!it.enabled})">${it.enabled ? 'Pausar' : 'Ativar'}</button>
                <button class="danger" onclick="deleteItem('${it.id}')">Excluir</button>
            </div>
        </div>`;
    }).join("");
}

async function refreshState() {
    const r = await fetch("/state");
    const data = await r.json();
    if (typeof data.connected === "boolean") {
        setConnected(data.connected);
    }
    if (data.enabled) {
        btnToggleScheduler.className = "toggle-btn on";
        btnToggleScheduler.textContent = "Agendamento: ON";
    } else {
        btnToggleScheduler.className = "toggle-btn";
        btnToggleScheduler.textContent = "Agendamento: OFF";
    }
    if (data.current_item) {
        const phase = data.phase === "gif" ? "GIF" : data.phase === "clock" ? "Rel&oacute;gio" : "ocioso";
        liveStatus.innerHTML = `<strong>Rodando:</strong> item ${data.current_item.substring(0, 8)}... &middot; fase: ${phase}`;
    } else {
        liveStatus.innerHTML = data.enabled ? "Agendamento ativo, mas nenhum item bate com o hor&aacute;rio atual." : "Agendamento desligado.";
    }
}

window.toggleItem = async (id, enabled) => {
    await postJSON("/schedule/toggle", {id, enabled});
    refreshSchedule();
};
window.deleteItem = async (id) => {
    if (!confirm("Excluir este agendamento?")) return;
    await postJSON("/schedule/delete", {id});
    refreshSchedule();
};

btnToggleScheduler.onclick = async () => {
    const r = await fetch("/state");
    const data = await r.json();
    const newEnabled = !data.enabled;
    await postJSON("/state", {enabled: newEnabled, pixels: parseInt(pixelsSel.value)});
    refreshState();
};

document.getElementById("scheduleForm").onsubmit = async (e) => {
    e.preventDefault();
    const fileInput = document.getElementById("schedGifFile");
    if (!fileInput.files.length) return;
    const days = Array.from(document.querySelectorAll("#daysContainer input:checked")).map(c => c.value);
    if (days.length === 0) {
        setStatus(schedStatus, false, "Selecione pelo menos um dia.");
        return;
    }
    const form = new FormData();
    form.append("file", fileInput.files[0]);
    form.append("start_time", document.getElementById("schedStart").value);
    form.append("end_time", document.getElementById("schedEnd").value);
    form.append("gif_seconds", document.getElementById("schedGifSec").value);
    form.append("clock_seconds", document.getElementById("schedClockSec").value);
    form.append("clock_style", document.getElementById("schedClockStyle").value);
    form.append("hour24", document.getElementById("schedClock24").value);
    form.append("visibleDate", document.getElementById("schedClockDate").value);
    form.append("r", document.getElementById("schedR").value);
    form.append("g", document.getElementById("schedG").value);
    form.append("b", document.getElementById("schedB").value);
    form.append("days", days.join(","));
    form.append("pixels", pixelsSel.value);
    try {
        const r = await fetch("/schedule/add", {method: "POST", body: form});
        const data = await r.json();
        setStatus(schedStatus, data.ok, data.ok ? "Agendamento adicionado!" : "Erro: " + data.error);
        if (data.ok) {
            fileInput.value = "";
            refreshSchedule();
        }
    } catch (err) {
        setStatus(schedStatus, false, "Erro: " + err);
    }
};

refreshSchedule();
refreshState();
setInterval(refreshState, 3000);
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/connect", methods=["POST"])
def connect():
    payload = request.get_json(silent=True) or {}
    address = payload.get("address")
    ok, addr, err = run_async(_connect(address))
    state = load_state()
    state["connected"] = bool(ok)
    if addr:
        state["address"] = addr
    save_state(state)
    return jsonify({"ok": ok, "address": addr, "error": err})


@app.route("/disconnect", methods=["POST"])
def disconnect():
    try:
        conn = ConnectionManager()
        run_async(conn.disconnect())
    except Exception:
        pass
    state = load_state()
    state["connected"] = False
    save_state(state)
    return jsonify({"ok": True})


@app.route("/clock", methods=["POST"])
def clock():
    payload = request.get_json(silent=True) or {}
    try:
        run_async(
            _set_clock(
                style=int(payload.get("style", 4)),
                hour24=bool(payload.get("hour24", True)),
                visible_date=bool(payload.get("visibleDate", True)),
                r=int(payload.get("r", 255)),
                g=int(payload.get("g", 255)),
                b=int(payload.get("b", 255)),
            )
        )
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/gif", methods=["POST"])
def gif():
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "Nenhum arquivo enviado"})
    f = request.files["file"]
    if not f.filename or not f.filename.lower().endswith(".gif"):
        return jsonify({"ok": False, "error": "Envie um arquivo .gif"})
    safe = secure_filename(f.filename)
    unique = f"{uuid.uuid4().hex}_{safe}"
    dest = os.path.join(app.config["UPLOAD_FOLDER"], unique)
    f.save(dest)
    pixel_size = int(request.form.get("pixels", 32))
    try:
        run_async(_send_gif(dest, pixel_size))
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/schedule", methods=["GET"])
def schedule_list():
    return jsonify({"items": load_schedule()})


@app.route("/schedule/add", methods=["POST"])
def schedule_add():
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "Arquivo obrigat\u00f3rio"})
    f = request.files["file"]
    if not f.filename or not f.filename.lower().endswith(".gif"):
        return jsonify({"ok": False, "error": "Envie um .gif"})
    safe = secure_filename(f.filename)
    unique = f"{uuid.uuid4().hex}_{safe}"
    gif_path = os.path.join(UPLOAD_FOLDER, unique)
    f.save(gif_path)
    days = [d.strip() for d in request.form.get("days", "").split(",") if d.strip()]
    item = {
        "id": uuid.uuid4().hex,
        "gif_path": gif_path,
        "gif_name": safe,
        "start_time": request.form.get("start_time", "08:00"),
        "end_time": request.form.get("end_time", "18:00"),
        "days": days,
        "gif_seconds": int(request.form.get("gif_seconds", 10)),
        "clock_seconds": int(request.form.get("clock_seconds", 14)),
        "clock_style": int(request.form.get("clock_style", 4)),
        "hour24": request.form.get("hour24", "1") == "1",
        "visibleDate": request.form.get("visibleDate", "1") == "1",
        "r": int(request.form.get("r", 255)),
        "g": int(request.form.get("g", 255)),
        "b": int(request.form.get("b", 255)),
        "enabled": True,
    }
    items = load_schedule()
    items.append(item)
    save_schedule(items)
    return jsonify({"ok": True, "id": item["id"]})


@app.route("/schedule/delete", methods=["POST"])
def schedule_delete():
    payload = request.get_json(silent=True) or {}
    item_id = payload.get("id")
    items = load_schedule()
    items = [it for it in items if it["id"] != item_id]
    save_schedule(items)
    return jsonify({"ok": True})


@app.route("/schedule/toggle", methods=["POST"])
def schedule_toggle():
    payload = request.get_json(silent=True) or {}
    item_id = payload.get("id")
    enabled = bool(payload.get("enabled", True))
    items = load_schedule()
    for it in items:
        if it["id"] == item_id:
            it["enabled"] = enabled
    save_schedule(items)
    return jsonify({"ok": True})


@app.route("/state", methods=["GET", "POST"])
def state():
    if request.method == "GET":
        return jsonify(load_state())
    payload = request.get_json(silent=True) or {}
    state = load_state()
    if "enabled" in payload:
        state["enabled"] = bool(payload["enabled"])
    if "pixels" in payload:
        state["pixels"] = int(payload["pixels"])
    save_state(state)
    return jsonify(state)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
