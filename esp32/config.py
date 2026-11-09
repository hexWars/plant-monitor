# =====================================
# Plant Monitor 配置文件
# 修改本文件即可调整设备参数，无需改动 main.py
# =====================================

# WiFi
WIFI_SSID = "caiweijie2"
WIFI_PASSWORD = "13652538312"
WIFI_TIMEOUT = 15                 # 秒
WIFI_RETRY_INTERVAL = 10          # 秒

# SHT35 温湿度传感器
I2C_ID = 0
I2C_SCL_PIN = 14
I2C_SDA_PIN = 13
I2C_FREQ = 100000
SHT35_ADDRESS = 0x44

# SH1106 OLED（SPI）
OLED_WIDTH = 128
OLED_HEIGHT = 64
OLED_SPI_ID = 2
OLED_SPI_BAUDRATE = 1000000
OLED_SCK_PIN = 36
OLED_MOSI_PIN = 37
OLED_CS_PIN = 40
OLED_DC_PIN = 39
OLED_RES_PIN = 38

# 本地历史统计：每120秒采样，按小时计算平均值
HISTORY_INTERVAL_MS = 120 * 1000

# NTP 时间同步
NTP_HOST = "pool.ntp.org"
NTP_RETRY_INTERVAL_MS = 5 * 60 * 1000
NTP_RESYNC_INTERVAL_MS = 6 * 60 * 60 * 1000
# MicroPython ESP32 time.time() 常见 epoch 为 2000-01-01
UNIX_EPOCH_OFFSET = 946684800


