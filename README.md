## Installation and libaries

Install libraries and dependencies using

```
pip install -r requirements-dev.txt
```


## Testing

To run Tests, run:

(For Mac/Linux in one line)

```
ALPACA_API_KEY=dummy ALPACA_SECRET_KEY=dummy DATABASE_URL=sqlite:///./test.db python -m pytest
```

(Windows Powershell)

```
$env:ALPACA_API_KEY="dummy"; $env:ALPACA_SECRET_KEY="dummy";

$env:DATABASE_URL="sqlite:///./test.db"; python -m pytest
```

#### To test using ALPACA

Run to load local web server:

```
uvicorn main:app --reload
```

And access: http://127.0.0.1:8000/docs


## Run locally

### Backend
On one terminal, run the backend on the root directory:

```
uvicorn main:app --reload
```

### Frontend
On a seperate terminal, switch to the frontend directory and run the frontend:

```
cd frontend
npm run dev
```


## Changing the database

Tables are created and changed by **Alembic migrations** in `migrations/versions/`, never by deleting the
database. The server applies any new migrations every time it starts, so you rarely run Alembic yourself.

When you change a model in `models.py` (add a column, change a type, add a table):

```
alembic revision --autogenerate -m "add bio to users"
```

1. Open the new file in `migrations/versions/` and check it does what you meant. Autogenerate can't tell a
   rename from "drop a column and add a new one", which would delete that column's data.
2. A new column on a table that already has rows must be `nullable=True` or have a `server_default`,
   or the migration fails on the live database.
3. Run the tests: `test_migrations.py` fails if `models.py` and the migrations disagree.
4. Commit the migration together with the `models.py` change.

Other commands: `alembic current` (which migration a database is at), `alembic history`,
`alembic downgrade -1` (undo the last migration, locally only).
