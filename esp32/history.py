import _thread

# 最多保存24个小时点：
# 每120秒接收一次样本，但只累计总和与数量，不保存每次原始读数。
MAX_HOURS = 24

_records = []
_lock = _thread.allocate_lock()

_current_hour = None
_temperature_sum = 0.0
_humidity_sum = 0.0
_sample_count = 0


def _finish_current_hour():
    """将当前小时的累计值汇总为一条平均值记录。调用时必须持有锁。"""
    global _records

    if _current_hour is None or _sample_count <= 0:
        return

    average_temperature = round(_temperature_sum / _sample_count, 2)
    average_humidity = round(_humidity_sum / _sample_count, 2)

    # 时间戳使用该小时的起始时刻，网页按北京时间显示。
    _records.append([
        int(_current_hour),
        average_temperature,
        average_humidity
    ])

    # 当前小时的实时平均值也会作为一个点返回，
    # 所以已完成小时最多保留23条，合计最多24条。
    while len(_records) > MAX_HOURS - 1:
        del _records[0]


def add_sample(timestamp, temperature, humidity):
    """累计一次样本；每小时只产生一条平均值，不保存每次原始读数。"""
    global _current_hour
    global _temperature_sum, _humidity_sum, _sample_count

    timestamp = int(timestamp)
    hour_start = timestamp - (timestamp % 3600)

    temperature = float(temperature)
    humidity = float(humidity)

    _lock.acquire()
    try:
        if _current_hour is None:
            _current_hour = hour_start

        elif hour_start != _current_hour:
            # 小时切换：先封存上一小时的平均值，再开始新小时。
            _finish_current_hour()

            _current_hour = hour_start
            _temperature_sum = 0.0
            _humidity_sum = 0.0
            _sample_count = 0

        _temperature_sum += temperature
        _humidity_sum += humidity
        _sample_count += 1

        # 按当前小时清理超过24小时的历史点。
        cutoff = hour_start - (MAX_HOURS - 1) * 3600
        while _records and _records[0][0] < cutoff:
            del _records[0]

    finally:
        _lock.release()


def get_history():
    """返回最多24条小时数据。当前小时返回正在累计的平均值。"""
    result = []

    _lock.acquire()
    try:
        for item in _records:
            result.append(item[:])

        if _current_hour is not None and _sample_count > 0:
            result.append([
                int(_current_hour),
                round(_temperature_sum / _sample_count, 2),
                round(_humidity_sum / _sample_count, 2)
            ])

        while len(result) > MAX_HOURS:
            del result[0]

    finally:
        _lock.release()

    return result


def count():
    return len(get_history())

