"""Windows 10 系统通知工具，支持 key 去重与自动过期。"""

import threading
import time

from winotify import Notification

# key → 过期时间戳（线程安全）
_expire_map: dict[str, float] = {}
_lock = threading.Lock()


def notify(
    title: str,
    message: str,
    key: str,
    cooldown: float = 1.0,
) -> bool:
    """弹出 Windows 10 系统通知。

    Args:
        title: 通知标题。
        message: 通知内容。
        key: 通知标识，相同 key 在 cooldown 时间内不会重复发送。
        cooldown: 去重冷却时间（分钟），默认 1 分钟后自动允许再次发送。

    Returns:
        True 表示通知已发送，False 表示冷却期内被跳过。
    """
    now = time.monotonic()
    with _lock:
        expire_at = _expire_map.get(key)
        if expire_at is not None and now < expire_at:
            return False
        _expire_map[key] = now + cooldown * 60

    n = Notification("Stock Monitor", title, message)
    n.show()
    return True


def reset_key(key: str) -> None:
    """立即移除某个 key 的冷却记录，允许该 key 再次发送通知。"""
    with _lock:
        _expire_map.pop(key, None)


def reset_all() -> None:
    """清空所有冷却记录。"""
    with _lock:
        _expire_map.clear()


if __name__ == "__main__":
    print("测试通知")
    notify("测试通知", "这是一条测试消息", key="test", cooldown=0.1)
