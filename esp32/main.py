from machine import Pin, I2C, SPI
import time
import network
import ntptime
import sh1106
import web_server
import history
import config


# 所有可调整参数统一放在 config.py 中。


# =====================================
# 1. OLED 初始化（提前到 WiFi 之前）
# =====================================

spi = SPI(
    config.OLED_SPI_ID,
    baudrate=config.OLED_SPI_BAUDRATE,
    polarity=0,
    phase=0,
    sck=Pin(config.OLED_SCK_PIN),
    mosi=Pin(config.OLED_MOSI_PIN),
    miso=None
)

cs = Pin(config.OLED_CS_PIN, Pin.OUT, value=1)
dc = Pin(config.OLED_DC_PIN, Pin.OUT)
res = Pin(config.OLED_RES_PIN, Pin.OUT)

oled = sh1106.SH1106_SPI(
    config.OLED_WIDTH,
    config.OLED_HEIGHT,
    spi,
    dc,
    res,
    cs
)


# 两片叶子共用同一组轮廓坐标，右侧通过镜像计算生成，确保左右完全对称。
# 每一项分别为：纵坐标、左叶起点、水平长度。
LEAF_ROWS = (
    (17, 53, 5),
    (18, 51, 8),
    (19, 49, 12),
    (20, 50, 13),
    (21, 53, 11),
    (22, 56, 8),
    (23, 59, 5),
    (24, 62, 2),
)


def draw_sprout(leaf_rows=8, stem_height=20, show_title=False):
    """绘制左右严格镜像的像素风幼苗。"""
    oled.fill(0)

    # 地面，整体以屏幕中心 x=63.5 对称
    oled.hline(42, 50, 44, 1)
    oled.hline(54, 51, 20, 1)

    # 种子
    oled.hline(61, 44, 6, 1)
    oled.hline(58, 45, 12, 1)
    oled.hline(57, 46, 14, 1)
    oled.hline(59, 47, 10, 1)
    oled.hline(62, 48, 4, 1)

    # 主茎采用两列像素，中心与屏幕中线对齐
    if stem_height > 0:
        stem_top = 45 - stem_height
        oled.vline(63, stem_top, stem_height, 1)
        oled.vline(64, stem_top, stem_height, 1)

    # 从叶片靠近茎的位置向外逐行展开，两侧使用镜像坐标
    visible_rows = LEAF_ROWS[-max(0, min(leaf_rows, len(LEAF_ROWS))):] if leaf_rows else ()

    for y, x, width in visible_rows:
        oled.hline(x, y, width, 1)
        right_x = 128 - x - width
        oled.hline(right_x, y, width, 1)

    # 叶脉也按中心线镜像绘制，避免两片叶子的角度不一致
    if leaf_rows >= 4:
        vein_points = (
            (62, 23), (61, 22), (60, 21), (58, 20),
            (56, 19), (54, 18), (53, 17)
        )
        for x, y in vein_points:
            oled.hline(x, y, 1, 0)
            oled.hline(127 - x, y, 1, 0)

    if show_title:
        oled.text("PLANT MONITOR", 12, 55)

    oled.show()


def play_boot_animation():
    """种子萌芽，茎生长，两片对称叶子同步展开。"""
    # 1. 种子
    draw_sprout(leaf_rows=0, stem_height=0)
    time.sleep_ms(350)

    # 2. 茎逐渐向上生长
    draw_sprout(leaf_rows=0, stem_height=10)
    time.sleep_ms(260)

    draw_sprout(leaf_rows=0, stem_height=20)
    time.sleep_ms(260)

    # 3. 两片叶子从靠近茎的位置向外同步展开
    for count in range(1, len(LEAF_ROWS) + 1):
        draw_sprout(leaf_rows=count, stem_height=20)
        time.sleep_ms(70)

    # 4. 显示设备名称
    draw_sprout(leaf_rows=len(LEAF_ROWS), stem_height=20, show_title=True)
    time.sleep_ms(550)


# 开机立即播放动画，不必等待 WiFi 连接
play_boot_animation()


# =====================================
# 2. WiFi 初始化与连接
# =====================================

wlan = network.WLAN(network.STA_IF)
wlan.active(True)


def connect_wifi():
    if wlan.isconnected():
        return True

    print("正在连接 WiFi:", config.WIFI_SSID)

    try:
        wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
    except Exception as e:
        print("WiFi启动连接失败:", e)
        return False

    start_time = time.time()

    while not wlan.isconnected():
        if time.time() - start_time > config.WIFI_TIMEOUT:
            print("WiFi连接超时")
            return False
        time.sleep(0.5)

    print("WiFi连接成功")
    print("SSID:", wlan.config("essid"))
    print("IP:", wlan.ifconfig()[0])
    return True


# =====================================
# 3. NTP 网络时间同步
# =====================================

time_synced = False
last_ntp_attempt = None


def sync_network_time(force=False):
    global time_synced, last_ntp_attempt

    if not wlan.isconnected():
        return False

    now = time.ticks_ms()

    if last_ntp_attempt is not None and not force:
        interval = config.NTP_RESYNC_INTERVAL_MS if time_synced else config.NTP_RETRY_INTERVAL_MS
        if time.ticks_diff(now, last_ntp_attempt) < interval:
            return time_synced

    last_ntp_attempt = now

    try:
        ntptime.host = config.NTP_HOST
        ntptime.settime()
        time_synced = True
        print("NTP时间同步成功")
        print("UTC时间:", time.gmtime())
        return True

    except Exception as e:
        time_synced = False
        print("NTP时间同步失败:", e)
        return False


def get_unix_timestamp():
    if not time_synced:
        return None

    try:
        current = time.time()
        if current < 700000000:
            return None
        return int(current + config.UNIX_EPOCH_OFFSET)
    except Exception:
        return None


# 初次连接 WiFi 并同步时间
connect_wifi()
sync_network_time(force=True)


# =====================================
# 4. SHT35 温湿度传感器初始化
# =====================================

i2c = I2C(
    config.I2C_ID,
    scl=Pin(config.I2C_SCL_PIN),
    sda=Pin(config.I2C_SDA_PIN),
    freq=config.I2C_FREQ
)



# =====================================
# 5. WiFi 信息获取
# =====================================

def get_wifi_info():
    if wlan.isconnected():
        return wlan.ifconfig()[0]
    return "NETWORK ERROR"


# =====================================
# 6. 读取 SHT35 温湿度
# =====================================

def read_sht35():
    i2c.writeto(config.SHT35_ADDRESS, b'\x24\x00')
    time.sleep_ms(20)

    data = i2c.readfrom(config.SHT35_ADDRESS, 6)

    raw_temp = data[0] * 256 + data[1]
    raw_humidity = data[3] * 256 + data[4]

    temperature = -45 + 175 * raw_temp / 65535
    humidity = 100 * raw_humidity / 65535

    return temperature, humidity


# =====================================
# 7. OLED 显示界面
# =====================================

def display_data(temperature, humidity):
    oled.fill(0)

    oled.text("PLANT MONITOR", 12, 2)
    oled.hline(0, 13, 128, 1)

    oled.text("TEMP", 4, 21)
    oled.text("{:.2f} C".format(temperature), 4, 32)

    oled.vline(63, 19, 34, 1)

    oled.text("RH", 70, 21)
    oled.text("{:.2f} %".format(humidity), 70, 32)

    oled.hline(0, 52, 128, 1)

    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        x = (128 - len(ip) * 8) // 2
        oled.text(ip, x, 55)
    else:
        oled.text("NETWORK ERROR", 8, 55)

    oled.show()


# =====================================
# 8. 启动 Web Server
# =====================================

web_server.update_data(
    None,
    None,
    get_wifi_info(),
    wlan.isconnected()
)

web_server.start_server()


# =====================================
# 9. 主循环
# =====================================

last_wifi_retry = time.time()
last_history_sample = None

while True:
    try:
        # WiFi 断线重连
        if not wlan.isconnected():
            if time.time() - last_wifi_retry >= config.WIFI_RETRY_INTERVAL:
                print("WiFi断开，尝试重新连接...")
                if connect_wifi():
                    sync_network_time(force=True)
                last_wifi_retry = time.time()
        else:
            # 未同步时每5分钟重试；已同步时每6小时校准
            sync_network_time()

        # 读取实时温湿度
        temperature, humidity = read_sht35()
        temperature = round(temperature, 2)
        humidity = round(humidity, 2)

        print("温度: {:.2f} ℃".format(temperature))
        print("湿度: {:.2f} %".format(humidity))

        ip = get_wifi_info()
        print("IP:", ip)
        print("------------------------")

        # OLED 每2秒刷新
        display_data(temperature, humidity)

        # 更新网页实时数据
        web_server.update_data(
            temperature,
            humidity,
            ip,
            wlan.isconnected()
        )

        # 每120秒采样一次，history.py 只累计当前小时的总和与数量
        now_ticks = time.ticks_ms()

        if (
            last_history_sample is None
            or time.ticks_diff(now_ticks, last_history_sample) >= config.HISTORY_INTERVAL_MS
        ):
            timestamp = get_unix_timestamp()

            if timestamp is not None:
                history.add_sample(timestamp, temperature, humidity)
                last_history_sample = now_ticks
                print("当前小时历史点数:", history.count())
            else:
                print("系统时间尚未同步，暂不累计历史数据")

    except Exception as e:
        print("读取失败:", e)

        web_server.update_data(
            None,
            None,
            get_wifi_info(),
            wlan.isconnected()
        )

        oled.fill(0)
        oled.text("SENSOR ERROR", 10, 20)
        oled.text("CHECK SHT35", 10, 36)
        oled.show()

    time.sleep(2)

