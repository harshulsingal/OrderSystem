# OrderSystem

Distributed Order & Inventory Management System backend built with FastAPI.

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (recommended)

## Project Structure

```text
OrderSystem/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── core/
│   │   └── __init__.py
│   ├── models/
│   │   └── __init__.py
│   ├── schemas/
│   │   └── __init__.py
│   ├── services/
│   │   └── __init__.py
│   ├── api/
│   │   └── __init__.py
│   └── kafka/
│       └── __init__.py
├── tests/
│   └── __init__.py
├── .env
├── .gitignore
├── README.md
└── pyproject.toml
```

## Setup & Installation

Install dependencies using `uv`:

```bash
uv sync
```

## Running the Server

Start the development server with reload enabled:

```bash
uv run uvicorn app.main:app --reload
```

or if the virtual environment is activated (`source .venv/bin/activate`):

```bash
uvicorn app.main:app --reload
```

## Health Check

Visit `http://localhost:8000/` or run:

```bash
curl http://localhost:8000/
```

Response:
```json
{"message": "Order System is running"}
```

## Order & Payment Workflow

1. **`POST /api/orders`** validates stock and reserves inventory in a single
   transaction, locking each product's inventory row (`SELECT ... FOR UPDATE`)
   in deterministic sorted order to prevent overselling and deadlocks under
   concurrent requests. The order is created with status `INVENTORY_RESERVED`
   and an `order.created` event is published to Kafka.
2. **`POST /api/payments`** creates an idempotent payment for the order. Retrying
   the same request with the same `idempotency_key` always returns the original
   payment instead of charging twice - enforced by a unique DB constraint, a
   best-effort Redis lock/cache for the fast path, and a row-locked read before
   the simulated gateway call. A `payment.requested` event is published to Kafka;
   a background consumer processes it asynchronously, and the request also
   processes inline so the API keeps working even without a running broker.
   - On success: the order moves to `PAID` and a `payment.completed` event fires.
   - On failure: the order moves to `PAYMENT_FAILED`, the reserved inventory is
     released back to `available_quantity` (compensating transaction), and a
     `payment.failed` event fires. Reusing the failed order's ID retries payment.
   - For demos/tests, prefixing `idempotency_key` with `FAIL` simulates a
     declined charge.

Kafka and Redis are both optional at runtime: if either is unreachable, the
corresponding calls fail fast and log a warning rather than blocking or
failing the request, so the API remains fully functional with just PostgreSQL.

## Configuration

Environment variables (see `.env`):

| Variable | Description | Default |
| --- | --- | --- |
| `DATABASE_URL` | PostgreSQL connection string | *required* |
| `REDIS_HOST` / `REDIS_PORT` | Redis used for idempotency caching and locks | `localhost` / `6379` |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka broker(s) for order/payment events | `localhost:9092` |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | Used by `/api/demo/generate` to create demo data | - |

> **Note:** `.env` is git-ignored - never commit real credentials or API keys to
> version control. Rotate any key that has ever been committed or shared.

