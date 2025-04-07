PROJECT_NAME = log-analyzer
CONFIG_PATH = configs/log_analyzer.yaml

.PHONY: help install run test lint mypy clean

help:
	@echo "📦 $(PROJECT_NAME)"
	@echo ""
	@echo " make install       Установка зависимостей (uv + editable)"
	@echo " make run           Запуск лог-анализатора"
	@echo " make test          Запуск pytest"
	@echo " make lint          Проверка кода ruff"
	@echo " make mypy          Статическая проверка mypy"
	@echo " make clean         Очистка *.pyc, __pycache__ и .pytest_cache"

install:
	uv pip install -e .

install-dev:
	uv pip install -e .[dev]

run:
	python src/log_analyzer/main.py --config $(CONFIG_PATH)

test:
	pytest tests/

lint:
	uv run ruff check src/ tests/

mypy:
	uv run mypy src/ tests/

clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
