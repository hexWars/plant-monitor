
const API_VERSION = "v1";
const MAX_BODY_SIZE = 1024;
const MAX_HISTORY_LIMIT = 100;
const RETENTION_SECONDS = 365 * 86400;

// =====================================
// 统一 JSON 响应
// =====================================

function json(data, status = 200) {
    return new Response(JSON.stringify(data), {
        status,
        headers: {
            "Content-Type": "application/json; charset=utf-8",
            "Cache-Control": "no-store",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization"
        }
    });
}

function error(message, status = 400) {
    return json({
        success: false,
        error: message
    }, status);
}

// =====================================
// 工具函数
// =====================================

function isValidNumber(value) {
    return typeof value === "number" && Number.isFinite(value);
}

function isValidTimestamp(value) {
    return Number.isSafeInteger(value) && value > 1000000000;
}

function constantTimeEqual(a, b) {
    if (typeof a !== "string" || typeof b !== "string") {
        return false;
    }

    if (a.length !== b.length) {
        return false;
    }

    let result = 0;

    for (let i = 0; i < a.length; i++) {
        result |= a.charCodeAt(i) ^ b.charCodeAt(i);
    }

    return result === 0;
}

function getDeviceId(url, env) {
    return url.searchParams.get("device_id") || env.DEVICE_ID;
}

function getShanghaiDate(timestamp = Date.now()) {
    return new Date(timestamp + 8 * 3600000)
        .toISOString()
        .slice(0, 10);
}

function getShanghaiDayRange(date) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) {
        return null;
    }

    const [year, month, day] = date.split("-").map(Number);

    const utcMidnight = Date.UTC(year, month - 1, day);

    const normalized = new Date(utcMidnight)
        .toISOString()
        .slice(0, 10);

    if (normalized !== date) {
        return null;
    }

    // 北京时间比 UTC 快8小时
    const start = utcMidnight / 1000 - 8 * 3600;

    return {
        start,
        end: start + 86400
    };
}

// =====================================
// Token 验证
// =====================================

function authenticate(request, env) {
    const authorization = request.headers.get("Authorization");

    if (!authorization || !env.DEVICE_TOKEN) {
        return false;
    }

    const expected = `Bearer ${env.DEVICE_TOKEN}`;

    return constantTimeEqual(authorization, expected);
}

// =====================================
// 1. 设备上传接口
// POST /api/v1/ingest
// =====================================

async function ingest(request, env) {
    if (!authenticate(request, env)) {
        return error("Unauthorized", 401);
    }

    const contentType = request.headers.get("Content-Type") || "";

    if (!contentType.toLowerCase().includes("application/json")) {
        return error("Content-Type must be application/json", 415);
    }

    const contentLength = Number(
        request.headers.get("Content-Length") || 0
    );

    if (contentLength > MAX_BODY_SIZE) {
        return error("Request body too large", 413);
    }

    let data;

    try {
        const body = await request.text();

        if (body.length > MAX_BODY_SIZE) {
            return error("Request body too large", 413);
        }

        data = JSON.parse(body);
    } catch {
        return error("Invalid JSON", 400);
    }

    const {
        device_id,
        timestamp,
        temperature,
        humidity
    } = data;

    // 设备 ID 校验
    if (
        typeof device_id !== "string" ||
        device_id !== env.DEVICE_ID
    ) {
        return error("Invalid device_id", 400);
    }

    // 时间戳校验
    if (!isValidTimestamp(timestamp)) {
        return error("Invalid timestamp", 400);
    }

    const now = Math.floor(Date.now() / 1000);

    // 不允许明显的未来时间
    if (timestamp > now + 300) {
        return error("Timestamp is too far in the future", 400);
    }

    // 不接受超过365天的数据
    if (timestamp < now - RETENTION_SECONDS) {
        return error("Data is outside retention period", 400);
    }

    // 温度校验
    if (
        !isValidNumber(temperature) ||
        temperature < -20 ||
        temperature > 80
    ) {
        return error("Invalid temperature", 400);
    }

    // 湿度校验
    if (
        !isValidNumber(humidity) ||
        humidity < 0 ||
        humidity > 100
    ) {
        return error("Invalid humidity", 400);
    }

    try {
        const result = await env.DB.prepare(`
      INSERT OR IGNORE INTO sensor_readings
      (
        device_id,
        timestamp,
        temperature,
        humidity
      )
      VALUES (?, ?, ?, ?)
    `).bind(
            device_id,
            timestamp,
            temperature,
            humidity
        ).run();

        const inserted = result.meta.changes > 0;

        return json({
            success: true,
            inserted,
            message: inserted
                ? "record accepted"
                : "duplicate record"
        }, inserted ? 201 : 200);

    } catch (err) {
        console.error("Ingest error:", err);
        return error("Database write failed", 500);
    }
}

// =====================================
// 2. 最新数据
// GET /api/v1/latest
// =====================================

async function latest(url, env) {
    const deviceId = getDeviceId(url, env);

    try {
        const data = await env.DB.prepare(`
      SELECT
        device_id,
        timestamp,
        temperature,
        humidity
      FROM sensor_readings
      WHERE device_id = ?
      ORDER BY timestamp DESC
      LIMIT 1
    `).bind(deviceId).first();

        return json({
            success: true,
            data: data || null,
            server_time: Math.floor(Date.now() / 1000)
        });

    } catch (err) {
        console.error("Latest query error:", err);
        return error("Database query failed", 500);
    }
}

// =====================================
// 3. 历史曲线
// GET /api/v1/series?range=24h
// =====================================

async function series(url, env) {
    const deviceId = getDeviceId(url, env);
    const range = url.searchParams.get("range") || "24h";

    const now = Math.floor(Date.now() / 1000);

    const ranges = {
        "24h": 86400,
        "7d": 7 * 86400,
        "30d": 30 * 86400
    };

    if (!(range in ranges)) {
        return error("Invalid range. Use 24h, 7d or 30d");
    }

    const start = now - ranges[range];

    try {
        let result;

        if (range === "24h") {
            // 24小时：返回原始数据
            result = await env.DB.prepare(`
        SELECT
          timestamp,
          temperature,
          humidity
        FROM sensor_readings
        WHERE device_id = ?
          AND timestamp >= ?
          AND timestamp <= ?
        ORDER BY timestamp ASC
        LIMIT 300
      `).bind(deviceId, start, now).all();

        } else {
            // 7天和30天：按小时聚合
            result = await env.DB.prepare(`
        SELECT
          CAST(timestamp / 3600 AS INTEGER) * 3600
            AS timestamp,

          AVG(temperature) AS temperature,

          AVG(humidity) AS humidity,

          COUNT(*) AS sample_count

        FROM sensor_readings

        WHERE device_id = ?
          AND timestamp >= ?
          AND timestamp <= ?

        GROUP BY CAST(timestamp / 3600 AS INTEGER)

        ORDER BY timestamp ASC
      `).bind(deviceId, start, now).all();
        }

        return json({
            success: true,
            range,
            count: result.results.length,
            data: result.results
        });

    } catch (err) {
        console.error("Series query error:", err);
        return error("Database query failed", 500);
    }
}

// =====================================
// 4. 历史记录分页
// GET /api/v1/history
// =====================================

async function history(url, env) {
    const deviceId = getDeviceId(url, env);

    const limit = Number(
        url.searchParams.get("limit") || 50
    );

    if (
        !Number.isInteger(limit) ||
        limit < 1 ||
        limit > MAX_HISTORY_LIMIT
    ) {
        return error("limit must be between 1 and 100");
    }

    const start = url.searchParams.get("start");
    const end = url.searchParams.get("end");
    const before = url.searchParams.get("before");

    const conditions = ["device_id = ?"];
    const bindings = [deviceId];

    if (start !== null) {
        const value = Number(start);

        if (!isValidTimestamp(value)) {
            return error("Invalid start timestamp");
        }

        conditions.push("timestamp >= ?");
        bindings.push(value);
    }

    if (end !== null) {
        const value = Number(end);

        if (!isValidTimestamp(value)) {
            return error("Invalid end timestamp");
        }

        conditions.push("timestamp < ?");
        bindings.push(value);
    }

    if (before !== null) {
        const value = Number(before);

        if (!isValidTimestamp(value)) {
            return error("Invalid before timestamp");
        }

        conditions.push("timestamp < ?");
        bindings.push(value);
    }

    if (
        start !== null &&
        end !== null &&
        Number(start) >= Number(end)
    ) {
        return error("start must be earlier than end");
    }

    const sql = `
    SELECT
      id,
      timestamp,
      temperature,
      humidity
    FROM sensor_readings
    WHERE ${conditions.join(" AND ")}
    ORDER BY timestamp DESC
    LIMIT ?
  `;

    bindings.push(limit + 1);

    try {
        const result = await env.DB.prepare(sql)
            .bind(...bindings)
            .all();

        const rows = result.results;

        const hasMore = rows.length > limit;
        const data = rows.slice(0, limit);

        return json({
            success: true,
            count: data.length,
            has_more: hasMore,
            next_before: hasMore
                ? data[data.length - 1].timestamp
                : null,
            data
        });

    } catch (err) {
        console.error("History query error:", err);
        return error("Database query failed", 500);
    }
}

// =====================================
// 5. 今日统计
// GET /api/v1/stats/daily
// =====================================

async function dailyStats(url, env) {
    const deviceId = getDeviceId(url, env);

    const date = url.searchParams.get("date")
        || getShanghaiDate();

    const range = getShanghaiDayRange(date);

    if (!range) {
        return error("Invalid date. Use YYYY-MM-DD");
    }

    try {
        const result = await env.DB.prepare(`
      SELECT
        COUNT(*) AS count,

        MIN(temperature) AS temperature_min,
        MAX(temperature) AS temperature_max,
        AVG(temperature) AS temperature_avg,

        MIN(humidity) AS humidity_min,
        MAX(humidity) AS humidity_max,
        AVG(humidity) AS humidity_avg

      FROM sensor_readings

      WHERE device_id = ?
        AND timestamp >= ?
        AND timestamp < ?
    `).bind(
            deviceId,
            range.start,
            range.end
        ).first();

        const hasData = result.count > 0;

        return json({
            success: true,
            date,
            count: result.count,

            temperature: {
                min: result.temperature_min,
                max: result.temperature_max,
                avg: result.temperature_avg
            },

            humidity: {
                min: result.humidity_min,
                max: result.humidity_max,
                avg: result.humidity_avg
            },

            has_data: hasData
        });

    } catch (err) {
        console.error("Stats query error:", err);
        return error("Database query failed", 500);
    }
}

// =====================================
// 6. 健康检查
// GET /api/v1/health
// =====================================

async function health(env) {
    try {
        await env.DB.prepare("SELECT 1 AS ok").first();

        return json({
            success: true,
            service: "plant-cabinet-api",
            version: API_VERSION,
            database: "connected",
            server_time: Math.floor(Date.now() / 1000)
        });

    } catch (err) {
        console.error("Health check error:", err);

        return json({
            success: false,
            service: "plant-cabinet-api",
            database: "unavailable"
        }, 503);
    }
}

// =====================================
// 7. 数据清理
// Cron: 每天北京时间03:00
// =====================================

async function cleanup(env) {
    const cutoff = Math.floor(Date.now() / 1000)
        - RETENTION_SECONDS;

    try {
        const result = await env.DB.prepare(`
      DELETE FROM sensor_readings
      WHERE timestamp < ?
    `).bind(cutoff).run();

        console.log("Retention cleanup completed:", {
            cutoff,
            deleted: result.meta.changes,
            time: new Date().toISOString()
        });

    } catch (err) {
        console.error("Retention cleanup failed:", err);
        throw err;
    }
}

// =====================================
// 8. Worker 入口
// =====================================

export default {
    async fetch(request, env) {
        const url = new URL(request.url);

        if (request.method === "OPTIONS") {
            return new Response(null, {
                status: 204,
                headers: {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization",
                    "Access-Control-Max-Age": "86400"
                }
            });
        }

        const path = url.pathname;

        if (path === "/api/v1/health" && request.method === "GET") {
            return health(env);
        }

        if (path === "/api/v1/ingest" && request.method === "POST") {
            return ingest(request, env);
        }

        if (request.method === "GET") {
            switch (path) {
                case "/api/v1/latest":
                    return latest(url, env);

                case "/api/v1/series":
                    return series(url, env);

                case "/api/v1/history":
                    return history(url, env);

                case "/api/v1/stats/daily":
                    return dailyStats(url, env);
            }
        }

        return error("API endpoint not found", 404);
    },

    async scheduled(controller, env) {
        console.log(
            "Scheduled task started:",
            controller.cron,
            new Date(controller.scheduledTime).toISOString()
        );

        await cleanup(env);
    }
};
