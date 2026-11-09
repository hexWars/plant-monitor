import socket
import _thread
import ujson
import time
import history


# =====================================
# 1. 实时数据
# =====================================

sensor_data = {
    "temperature": None,
    "humidity": None,
    "ip": "NETWORK ERROR",
    "connected": False
}


def update_data(temperature, humidity, ip, connected):
    global sensor_data

    sensor_data = {
        "temperature": temperature,
        "humidity": humidity,
        "ip": ip,
        "connected": connected
    }


# =====================================
# 2. 网页 HTML
# =====================================

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#101812">
<title>Plant Monitor</title>

<style>
* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    min-height: 100vh;
    background: #101812;
    color: #edf3ec;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    padding: 32px 20px;
}

.container {
    max-width: 900px;
    margin: 0 auto;
}

.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 42px;
    gap: 12px;
}

.brand {
    display: flex;
    align-items: center;
    gap: 12px;
}

.logo {
    width: 42px;
    height: 42px;
    border-radius: 14px;
    background: #263b2b;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 22px;
}

.brand h1 {
    font-size: 17px;
    font-weight: 600;
    letter-spacing: 1px;
}

.brand p {
    font-size: 11px;
    color: #829184;
    margin-top: 4px;
    letter-spacing: 1.5px;
}

.status {
    display: flex;
    align-items: center;
    gap: 7px;
    color: #8bba91;
    font-size: 12px;
}

.dot {
    width: 7px;
    height: 7px;
    background: #72c887;
    border-radius: 50%;
    box-shadow: 0 0 10px #72c887;
}

.dot.offline {
    background: #e07878;
    box-shadow: 0 0 10px #e07878;
}

.section-label {
    color: #829184;
    font-size: 11px;
    letter-spacing: 2px;
    margin-bottom: 16px;
}

.cards {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
}

.card {
    background: #1a261e;
    border: 1px solid #2b3b30;
    border-radius: 20px;
    padding: 25px;
    min-height: 190px;
}

.card-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.card-label {
    font-size: 12px;
    color: #91a295;
    letter-spacing: 1.5px;
}

.card-icon {
    width: 34px;
    height: 34px;
    border-radius: 11px;
    background: #2a3c30;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 17px;
}

.value {
    margin-top: 30px;
    font-size: clamp(34px, 8vw, 48px);
    font-weight: 500;
    letter-spacing: -2px;
    line-height: 1;
}

.unit {
    font-size: 17px;
    color: #a4b5a7;
    margin-left: 4px;
    letter-spacing: 0;
}

.card-footer {
    margin-top: 15px;
    font-size: 11px;
    color: #78897b;
}

.info-section {
    margin-top: 34px;
}

.info-card {
    background: #1a261e;
    border: 1px solid #2b3b30;
    border-radius: 16px;
    padding: 5px 20px;
}

.info-row {
    min-height: 57px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #2b3b30;
    gap: 12px;
}

.info-row:last-child {
    border-bottom: none;
}

.info-label {
    font-size: 12px;
    color: #91a295;
}

.info-value {
    font-size: 12px;
    color: #dce9dc;
    font-family: monospace;
    text-align: right;
    overflow-wrap: anywhere;
}

.history-section {
    margin-top: 38px;
}

.chart-card {
    background: #1a261e;
    border: 1px solid #2b3b30;
    border-radius: 18px;
    padding: 22px;
    margin-bottom: 16px;
}

.chart-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 8px;
}

.chart-title {
    font-size: 12px;
    color: #91a295;
    letter-spacing: 1.5px;
}

.chart-range {
    font-size: 10px;
    color: #829184;
    border: 1px solid #354638;
    padding: 5px 8px;
    border-radius: 20px;
}

.chart-current {
    font-size: 27px;
    font-weight: 500;
    letter-spacing: -1px;
    margin: 12px 0 4px;
}

.chart-subtitle {
    font-size: 11px;
    color: #78897b;
    margin-bottom: 12px;
}

.chart-wrap {
    position: relative;
    width: 100%;
    height: 190px;
}

canvas {
    display: block;
    width: 100%;
    height: 100%;
    touch-action: pan-y;
}

.chart-legend {
    display: flex;
    gap: 16px;
    margin-top: 10px;
    font-size: 10px;
    color: #829184;
}

.legend-item {
    display: flex;
    align-items: center;
    gap: 6px;
}

.legend-line {
    width: 16px;
    height: 2px;
    border-radius: 2px;
}

.history-meta {
    color: #78897b;
    font-size: 11px;
    margin-top: 6px;
    line-height: 1.7;
}

.footer {
    margin-top: 34px;
    display: flex;
    justify-content: space-between;
    color: #647468;
    font-size: 11px;
    gap: 12px;
}

@media (max-width: 480px) {
    body {
        padding: 24px 16px;
    }

    .header {
        margin-bottom: 32px;
    }

    .cards {
        gap: 10px;
    }

    .card {
        padding: 18px 14px;
        min-height: 170px;
    }

    .value {
        font-size: 34px;
        margin-top: 28px;
    }

    .unit {
        font-size: 14px;
    }

    .chart-card {
        padding: 17px 13px;
    }

    .chart-wrap {
        height: 175px;
    }
}
</style>
</head>

<body>
<div class="container">

    <header class="header">
        <div class="brand">
            <div class="logo">🌿</div>
            <div>
                <h1>PLANT MONITOR</h1>
                <p>ENVIRONMENT SYSTEM</p>
            </div>
        </div>

        <div class="status">
            <span class="dot" id="statusDot"></span>
            <span id="statusText">CONNECTED</span>
        </div>
    </header>

    <div class="section-label">ENVIRONMENT</div>

    <div class="cards">
        <div class="card">
            <div class="card-top">
                <span class="card-label">TEMPERATURE</span>
                <span class="card-icon">🌡</span>
            </div>
            <div class="value">
                <span id="temperature">--.--</span><span class="unit">°C</span>
            </div>
            <div class="card-footer">Current temperature</div>
        </div>

        <div class="card">
            <div class="card-top">
                <span class="card-label">HUMIDITY</span>
                <span class="card-icon">💧</span>
            </div>
            <div class="value">
                <span id="humidity">--.--</span><span class="unit">%</span>
            </div>
            <div class="card-footer">Relative humidity</div>
        </div>
    </div>

    <div class="info-section">
        <div class="section-label">DEVICE INFORMATION</div>
        <div class="info-card">
            <div class="info-row">
                <span class="info-label">DEVICE</span>
                <span class="info-value">ESP32-S3</span>
            </div>
            <div class="info-row">
                <span class="info-label">IP ADDRESS</span>
                <span class="info-value" id="ip">--</span>
            </div>
            <div class="info-row">
                <span class="info-label">NETWORK</span>
                <span class="info-value" id="network">OFFLINE</span>
            </div>
            <div class="info-row">
                <span class="info-label">LAST UPDATE</span>
                <span class="info-value" id="updateTime">--:--:--</span>
            </div>
        </div>
    </div>

    <div class="history-section">
        <div class="section-label">24 HOURS HISTORY</div>

        <div class="chart-card">
            <div class="chart-header">
                <span class="chart-title">TEMPERATURE</span>
                <span class="chart-range">LAST 24 HOURS</span>
            </div>
            <div class="chart-current">
                <span id="chartTempCurrent">--.--</span> °C
            </div>
            <div class="chart-subtitle">Temperature trend</div>
            <div class="chart-wrap">
                <canvas id="tempChart"></canvas>
            </div>
        </div>

        <div class="chart-card">
            <div class="chart-header">
                <span class="chart-title">HUMIDITY</span>
                <span class="chart-range">LAST 24 HOURS</span>
            </div>
            <div class="chart-current">
                <span id="chartHumidityCurrent">--.--</span> %
            </div>
            <div class="chart-subtitle">Relative humidity trend</div>
            <div class="chart-wrap">
                <canvas id="humidityChart"></canvas>
            </div>
        </div>

        <div class="history-meta" id="historyMeta">
            Waiting for hourly averages...
        </div>
    </div>

    <footer class="footer">
        <span>PLANT MONITOR SYSTEM</span>
        <span>LIVE · 2S / HISTORY · 120S</span>
    </footer>
</div>

<script>
let historySamples = [];
let tempChartInstance = null;
let humidityChartInstance = null;

function formatTime(timestamp) {
    return new Date(timestamp * 1000).toLocaleTimeString("zh-CN", {
        timeZone: "Asia/Shanghai",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false
    });
}

function formatDateTime(timestamp) {
    return new Date(timestamp * 1000).toLocaleString("zh-CN", {
        timeZone: "Asia/Shanghai",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false
    });
}

function drawChart(canvasId, dataIndex, lineColor, unit, chartInstanceName) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const width = Math.max(280, Math.floor(rect.width));
    const height = Math.max(140, Math.floor(rect.height));
    const dpr = window.devicePixelRatio || 1;

    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);

    const ctx = canvas.getContext("2d");
    ctx.scale(dpr, dpr);

    const left = 39;
    const right = width - 9;
    const top = 12;
    const bottom = height - 27;
    const plotWidth = right - left;
    const plotHeight = bottom - top;

    ctx.clearRect(0, 0, width, height);

    if (historySamples.length === 0) {
        ctx.fillStyle = "#829184";
        ctx.font = "12px sans-serif";
        ctx.textAlign = "center";
        ctx.fillText("No historical data yet", width / 2, height / 2);
        return;
    }

    const values = historySamples.map(item => Number(item[dataIndex]));
    let minValue = Math.min(...values);
    let maxValue = Math.max(...values);

    if (maxValue - minValue < 1) {
        minValue -= 0.5;
        maxValue += 0.5;
    } else {
        const padding = (maxValue - minValue) * 0.12;
        minValue -= padding;
        maxValue += padding;
    }

    const xFor = index => left + (index / Math.max(1, historySamples.length - 1)) * plotWidth;
    const yFor = value => bottom - ((value - minValue) / (maxValue - minValue)) * plotHeight;

    // 网格与纵轴刻度
    ctx.strokeStyle = "#354638";
    ctx.lineWidth = 1;
    ctx.fillStyle = "#829184";
    ctx.font = "10px sans-serif";
    ctx.textAlign = "right";

    for (let i = 0; i <= 4; i++) {
        const y = top + (plotHeight / 4) * i;
        const value = maxValue - ((maxValue - minValue) / 4) * i;

        ctx.beginPath();
        ctx.setLineDash([3, 4]);
        ctx.moveTo(left, y);
        ctx.lineTo(right, y);
        ctx.stroke();

        ctx.setLineDash([]);
        ctx.fillText(value.toFixed(1), left - 7, y + 3);
    }

    // 时间轴
    ctx.textAlign = "center";
    const labels = 4;
    for (let i = 0; i <= labels; i++) {
        const x = left + (plotWidth / labels) * i;
        const sampleIndex = Math.round((historySamples.length - 1) * i / labels);
        const sample = historySamples[sampleIndex];

        if (sample) {
            ctx.fillText(formatTime(sample[0]), x, height - 8);
        }
    }

    // 折线
    ctx.beginPath();
    ctx.lineWidth = 2;
    ctx.strokeStyle = lineColor;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";

    historySamples.forEach((item, index) => {
        const x = xFor(index);
        const y = yFor(Number(item[dataIndex]));

        if (index === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });

    ctx.stroke();

    // 当前数据点
    const last = historySamples[historySamples.length - 1];
    if (last) {
        const x = xFor(historySamples.length - 1);
        const y = yFor(Number(last[dataIndex]));

        ctx.beginPath();
        ctx.arc(x, y, 3.5, 0, Math.PI * 2);
        ctx.fillStyle = lineColor;
        ctx.fill();
    }

    // 保存绘图参数，供触摸/鼠标查看
    canvas._chartInfo = {
        dataIndex, left, right, top, bottom,
        minValue, maxValue, plotWidth, plotHeight,
        width, height
    };

    canvas._chartSamples = historySamples;
}

function drawAllCharts() {
    drawChart("tempChart", 1, "#83c995", "°C", "tempChartInstance");
    drawChart("humidityChart", 2, "#78b9d6", "%", "humidityChartInstance");

    if (historySamples.length > 0) {
        const latest = historySamples[historySamples.length - 1];
        document.getElementById("chartTempCurrent").textContent =
            Number(latest[1]).toFixed(2);
        document.getElementById("chartHumidityCurrent").textContent =
            Number(latest[2]).toFixed(2);

        const first = historySamples[0][0];
        const last = historySamples[historySamples.length - 1][0];

        document.getElementById("historyMeta").textContent =
            "Hourly points: " + historySamples.length +
            " / 24 · From " + formatDateTime(first) +
            " to " + formatDateTime(last) +
            " · Average per hour (sampled every 120s)";
    } else {
        document.getElementById("historyMeta").textContent =
            "No hourly data yet. Waiting for samples...";
    }
}

async function updateData() {
    try {
        const response = await fetch("/api/data", {cache: "no-store"});
        if (!response.ok) throw new Error("Network error");

        const data = await response.json();

        document.getElementById("temperature").textContent =
            data.temperature === null ? "--.--" : Number(data.temperature).toFixed(2);

        document.getElementById("humidity").textContent =
            data.humidity === null ? "--.--" : Number(data.humidity).toFixed(2);

        document.getElementById("ip").textContent = data.ip;
        document.getElementById("network").textContent =
            data.connected ? "CONNECTED" : "DISCONNECTED";

        document.getElementById("statusText").textContent =
            data.connected ? "CONNECTED" : "OFFLINE";

        document.getElementById("statusDot").className =
            data.connected ? "dot" : "dot offline";

        document.getElementById("updateTime").textContent =
            new Date().toLocaleTimeString("zh-CN", {
                timeZone: "Asia/Shanghai",
                hour12: false
            });

    } catch (error) {
        document.getElementById("statusText").textContent = "OFFLINE";
        document.getElementById("statusDot").className = "dot offline";
    }
}

async function updateHistory() {
    try {
        const response = await fetch("/api/history", {cache: "no-store"});
        if (!response.ok) throw new Error("History request failed");

        const data = await response.json();
        historySamples = Array.isArray(data.samples) ? data.samples : [];
        drawAllCharts();

    } catch (error) {
        document.getElementById("historyMeta").textContent =
            "Unable to load historical data";
    }
}

// 鼠标或触摸时显示对应采样点信息
function enableChartInspection(canvasId, dataIndex, label, unit) {
    const canvas = document.getElementById(canvasId);

    function inspect(event) {
        const info = canvas._chartInfo;
        const samples = canvas._chartSamples;
        if (!info || !samples || samples.length === 0) return;

        const rect = canvas.getBoundingClientRect();
        const clientX = event.clientX !== undefined
            ? event.clientX
            : event.touches[0].clientX;

        const x = clientX - rect.left;
        const ratio = Math.max(0, Math.min(1,
            (x - info.left) / info.plotWidth
        ));
        const index = Math.round(ratio * (samples.length - 1));
        const sample = samples[index];

        const value = Number(sample[dataIndex]).toFixed(2);
        document.getElementById("historyMeta").textContent =
            formatDateTime(sample[0]) + " · " + label + ": " + value + unit;
    }

    canvas.addEventListener("mousemove", inspect);
    canvas.addEventListener("touchstart", inspect, {passive: true});
    canvas.addEventListener("touchmove", inspect, {passive: true});
}

enableChartInspection("tempChart", 1, "Temperature", " °C");
enableChartInspection("humidityChart", 2, "Humidity", " %");

updateData();
updateHistory();

setInterval(updateData, 2000);
setInterval(updateHistory, 120000);

window.addEventListener("resize", drawAllCharts);
</script>
</body>
</html>
"""


# =====================================
# 3. HTTP 响应
# =====================================

def send_response(conn, content, content_type, status="200 OK"):
    if isinstance(content, str):
        body = content.encode("utf-8")
    else:
        body = content

    header = (
        "HTTP/1.1 " + status + "\r\n"
        "Content-Type: " + content_type + "; charset=utf-8\r\n"
        "Content-Length: " + str(len(body)) + "\r\n"
        "Connection: close\r\n"
        "Cache-Control: no-store\r\n"
        "\r\n"
    )

    conn.sendall(header.encode("utf-8"))
    conn.sendall(body)


# =====================================
# 4. HTTP 请求处理
# =====================================

def handle_request(conn):
    try:
        request = conn.recv(1024)

        if not request:
            return

        request_line = request.split(b"\r\n", 1)[0]
        parts = request_line.split()

        if len(parts) < 2:
            return

        path = parts[1].decode()

        if path == "/" or path == "/index.html":
            send_response(conn, HTML, "text/html")

        elif path == "/api/data":
            data = ujson.dumps(sensor_data)
            send_response(conn, data, "application/json")

        elif path == "/api/history":
            payload = {
                "samples": history.get_history(),
                "count": history.count()
            }
            data = ujson.dumps(payload)
            send_response(conn, data, "application/json")

        else:
            send_response(
                conn,
                "404 Not Found",
                "text/plain",
                status="404 Not Found"
            )

    except Exception as e:
        print("HTTP Error:", e)


# =====================================
# 5. HTTP 服务
# =====================================

def server_loop():
    server = socket.socket()

    server.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    server.bind(("0.0.0.0", 80))
    server.listen(2)
    server.settimeout(1)

    print("Web Server Started")
    print("Port: 80")

    while True:
        try:
            conn, addr = server.accept()

            try:
                handle_request(conn)
            finally:
                conn.close()

        except OSError:
            pass

        except Exception as e:
            print("Server Error:", e)


def start_server():
    _thread.start_new_thread(server_loop, ())
    print("Web Server Starting...")

