# 🧾 Log Analyzer

Инструмент для парсинга логов nginx, подсчёта статистики по `URL` и генерации `HTML-отчёта`.

---

## Установка

Убедитесь, что у вас установлен [`uv`](https://github.com/astral-sh/uv):

```bash
git clone https://github.com/vasevooo/otus_python_professional.git
cd otus_python_professional
uv pip install -e .
```

## Использование Makefile

Для удобства проект содержит `Makefile` с основными командами:

| Команда             | Что делает                                      |
|---------------------|-------------------------------------------------|
| `make install`      | Устанавливает зависимости (`uv`)                |
| `make install-dev`  | Устанавливает dev зависимости (`uv`)            |
| `make run`          | Запускает анализатор логов                      |
| `make test`*        | Запускает тесты (`pytest`)                      |
| `make lint`*        | Проверяет стиль кода (`ruff`)                   |
| `make mypy`*        | Запускает проверку типов (`mypy`)               |
| `make clean`        | Удаляет `__pycache__`, `.pyc` и кеши            |

\* Команды помеченные `*` требуют установки dev-зависимостей:  
```bash
make install-dev
```

Примеры:

```bash
make install
make run
make test
```

##  Запуск (без `MakeFile`)

```
python src/log_analyzer/main.py --config configs/log_analyzer.yaml
```

## [Конфигурация](../../configs/log_analyzer.yaml)

| Опция | Описание | Дефолтное значение |
|--------|-------------|---------|
| `REPORT_SIZE` | Количество URL, включаемых в отчет | 100 |
| `REPORT_DIR` | Директория, где будут храниться отчеты | `reports` |
| `LOG_DIR` | Директория, где хранятся логи для анализа | `data` |
| `LOG_FILE` | Путь до файла, куда писать логи скрипта | `logs/log.log` |

### Пример файла-конфигурации

```json
{
    "REPORT_SIZE": 100,
    "REPORT_DIR": "reports",
    "LOG_DIR": "data",
    "LOG_FILE": "logs/log.log"
}
```


## Тестирование (без  `Makefile`)
```
pytest tests/
```

## Логирование
- До загрузки конфига лог пишет в `stdout` в читаемом виде (`ConsoleRenderer`)
- После загрузки — переключается на логирование в `JSON` (в файл, если указан `LOG_FILE`)
- Логи можно анализировать утилитами вроде `jq`

## Возможности
- Поддержка `.gz` логов
- Игнорирование некорректных строк
- Формирование отчёта с sortable-таблицей
- Повторная генерация отчёта не происходит, если он уже есть
- Структура проекта на базе src/, работает с `pyproject.toml`
