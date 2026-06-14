# Algo Trading Platform (Interactive Brokers)

Алгоритмическая торговая платформа на Python для работы через **Interactive Brokers**
(IB Gateway / TWS). Собственная архитектура: получение рыночных данных, генерация
сигналов, риск-менеджмент, OMS, автоматическое исполнение заявок, бэктестинг,
paper- и live-режимы, мониторинг.

> Демонстрационный каркас. Единый торговый pipeline переиспользуется в backtest /
> paper / live — стратегия, проверенная на истории, работает в продакшене без
> изменений (меняются только источник данных и шлюз исполнения).

## Возможности

- **Market data** — IB (ib_insync), реальные исторические данные (CSV-кэш, `scripts/fetch_data.py`) + детерминированный mock для тестов
- **Signals** — подключаемые стратегии (в комплекте SMA crossover)
- **Risk management** — лимиты на размер заявки, позицию, дневной убыток (kill-switch)
- **OMS** — учёт заявок и позиций, средняя цена, журналирование в Postgres
- **Execution** — paper-симуляция (slippage) и реальный шлюз IB
- **Backtesting** — событийный движок, тот же путь signal → risk → OMS
- **Paper / Live** — переключение через `TRADING_MODE`
- **Monitoring** — Prometheus метрики + Grafana, структурные логи (structlog)

## Стек

Python 3.11 · FastAPI · PostgreSQL · Redis · Docker · Interactive Brokers API
(ib_insync) · Prometheus · Grafana

## Архитектура

См. [docs/architecture.md](docs/architecture.md) — там диаграмма pipeline.

```
market data → signals → risk → OMS → execution
                                  ↘  Postgres (journal) / Redis (state)
              FastAPI /api /metrics → Prometheus → Grafana
```

## Структура

```
src/app/
  market_data/   IB + mock провайдеры (общий интерфейс)
  signals/       стратегии (SMA crossover)
  risk/          пред-торговые проверки
  oms/           учёт заявок и позиций
  execution/     paper-симуляция + IB шлюз
  backtest/      событийный бэктестер
  api/           FastAPI роуты
  db/            SQLAlchemy модели + сессии
  engine.py      сборка pipeline по TRADING_MODE
  main.py        FastAPI entrypoint (+ /metrics)
tests/           юнит-тесты (signals, risk, oms, backtest)
infra/           prometheus + grafana
```

## Быстрый старт (без Docker)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env

# демо: бэктест + одна сделка на mock-данных
PYTHONPATH=src python scripts/demo.py

# тесты
pytest -q
```

## Запуск через Docker

```bash
cp .env.example .env
docker compose up --build
```

- **Демо-страница**: http://localhost:8000/ — архитектура + интерактивный бэктест
  с equity-кривой (считается реальным backend-кодом через `POST /api/backtest`)
- API + Swagger: http://localhost:8000/docs
- Метрики: http://localhost:8000/metrics
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin / admin)

Пример бэктеста через API:

```bash
curl -X POST http://localhost:8000/api/backtest \
  -H "Content-Type: application/json" \
  -d '{"symbol":"AAPL","lookback":250,"fast":10,"slow":30}'
```

## Подключение к Interactive Brokers

1. Установить **IB Gateway** (проще) или **TWS** и залогиниться в paper-аккаунт.
2. Включить API: Settings → API → *Enable ActiveX and Socket Clients*; порт для
   paper — Gateway **4002**, TWS **7497**; добавить `127.0.0.1` в *Trusted IPs*.
3. В `.env` указать `IB_HOST`, `IB_PORT`, `IB_ACCOUNT` (id вида `DU…`) и
   `TRADING_MODE=paper_ib` (данные IB + симуляция исполнения) или `live`
   (реальные заявки).
4. Проверить живое подключение smoke-скриптом — он берёт исторические бары,
   подписывается на котировки и (опционально) выставляет тестовую заявку на
   paper-счёте:

```bash
PYTHONPATH=src python scripts/ib_smoke.py --symbol AAPL          # котировки + paper-заявка
PYTHONPATH=src python scripts/ib_smoke.py --symbol MSFT --no-order  # только данные, без заявки
```

Скрипт использует задержанные данные (delayed, бесплатны на paper) и выставляет
заявку только если `IB_ACCOUNT` похож на paper-счёт (`DU…`).

## Дисклеймер

Учебно-демонстрационный проект. Торговля сопряжена с риском потери капитала.
Перед использованием на реальном счёте проводите собственное тестирование.
