
-- =====================================
-- 热植柜温湿度监测数据库
-- Migration: 0001_initial
-- =====================================

CREATE TABLE IF NOT EXISTS sensor_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    device_id TEXT NOT NULL,

    timestamp INTEGER NOT NULL,

    temperature REAL NOT NULL,

    humidity REAL NOT NULL,

    created_at INTEGER NOT NULL DEFAULT (unixepoch()),

    UNIQUE(device_id, timestamp)
);

-- 用于全局过期数据清理
CREATE INDEX IF NOT EXISTS idx_sensor_timestamp
ON sensor_readings(timestamp);

-- 用于设备历史数据查询
CREATE INDEX IF NOT EXISTS idx_sensor_device_timestamp
ON sensor_readings(device_id, timestamp DESC);
