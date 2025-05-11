from scoring_api.scoring import Store


def test_get_success(redisdb):
    """Проверяем работу метода get"""
    store = Store(redis_client=redisdb)

    # Подготавливаем тестовые данные
    redisdb.set("test_key", "test_value")

    # Проверяем работу метода
    result = store.get("test_key")
    assert result == "test_value"


def test_get_not_found(redisdb):
    """Проверяем случай, когда ключ не существует"""
    store = Store(redis_client=redisdb)
    result = store.get("non_existent_key")
    assert result is None


def test_cache_get_success(redisdb):
    """Проверяем работу метода cache_get"""
    store = Store(redis_client=redisdb)

    # Подготавливаем тестовые данные
    redisdb.set("cache_key", "cached_value")

    # Проверяем работу метода
    result = store.cache_get("cache_key")
    assert result == "cached_value"


def test_cache_set_success(redisdb):
    """Проверяем работу метода cache_set"""
    store = Store(redis_client=redisdb)

    # Проверяем работу метода
    store.cache_set("cache_key", "cache_value", 60)

    # Проверяем результат
    assert redisdb.get("cache_key") == "cache_value"
    assert redisdb.ttl("cache_key") <= 60


def test_cache_set_with_timeout(redisdb):
    """Проверяем работу TTL в кэше"""
    store = Store(redis_client=redisdb)

    # Сохраняем данные с маленьким TTL
    store.cache_set("temp_key", "temp_value", 1)

    # Проверяем, что данные есть
    assert redisdb.get("temp_key") == "temp_value"

    # Ждем, пока TTL истечет
    import time

    time.sleep(1.1)

    # Проверяем, что данные исчезли
    assert redisdb.get("temp_key") is None
