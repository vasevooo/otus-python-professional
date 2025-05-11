import hashlib
import json
from datetime import datetime
from typing import Optional
from functools import wraps
import redis
import time


def retry_on_connection_error(max_retries=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except redis.ConnectionError:
                    retries += 1
                    if retries == max_retries:
                        raise
                    time.sleep(delay)
            return None

        return wrapper

    return decorator


class Store:
    def __init__(
        self, host="localhost", port=6379, db=0, socket_timeout=5, redis_client=None
    ):
        if redis_client is not None:
            self.redis = redis_client
        else:
            self.redis = redis.Redis(
                host=host,
                port=port,
                db=db,
                socket_timeout=socket_timeout,
                decode_responses=True,
            )

    @retry_on_connection_error(max_retries=3)
    def get(self, key: str) -> Optional[str]:
        """Получение данных из постоянного хранилища.
        Может выбросить исключение при недоступности хранилища"""
        try:
            return self.redis.get(key)
        except redis.RedisError:
            raise

    def cache_get(self, key: str) -> Optional[str]:
        """Получение данных из кэша.
        Возвращает None при любой ошибке (хранилище недоступно)"""
        try:
            return self.redis.get(key)
        except redis.RedisError:
            return None

    def cache_set(self, key: str, value: str, timeout: int) -> None:
        """ "Сохранение данных в кэш с таймаутом"""
        try:
            self.redis.setex(key, timeout, value)
        except redis.RedisError:
            pass


def get_score(
    store,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    birthday: Optional[datetime] = None,
    gender: Optional[int] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
) -> float:
    key_parts = [
        str(first_name) if first_name else "",
        str(last_name) if last_name else "",
        str(phone) if phone else "",
        birthday.strftime("%Y%m%d") if isinstance(birthday, datetime) else "",
    ]
    key = "uid:" + hashlib.md5("".join(key_parts).encode("utf-8")).hexdigest()

    # Try to get from cache
    score = store.cache_get(key)
    if score is not None:
        return float(score)

    # Calculate score
    score = 0.0
    if phone:
        score += 1.5
    if email:
        score += 1.5
    if birthday and gender is not None:
        score += 1.5
    if first_name and last_name:
        score += 0.5

    # Cache the score for 60 minutes
    store.cache_set(key, score, 60 * 60)
    return score


def get_interests(store, cid: str) -> list:
    r = store.get(f"i:{cid}")
    if r is None:
        return []
    try:
        interests = json.loads(r)
        if not isinstance(interests, list):
            return []
        return [str(i) for i in interests]
    except (json.JSONDecodeError, TypeError):
        return []
