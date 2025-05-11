# tests/conftest.py
from pytest_redis import factories

# Создаем фикстуру для Redis процесса
redis_proc = factories.redis_proc(
    port=None,  # Автоматически выберет свободный порт
    host="localhost",
)

# Создаем фикстуру для Redis клиента
redisdb = factories.redisdb("redis_proc")
