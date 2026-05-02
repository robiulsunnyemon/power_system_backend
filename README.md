# Jorden Backend

FastAPI Backend with Prisma and PostgreSQL.

## Setup
0. `poetry env activate`
1. Update `.env`
2. `poetry install`
3. `poetry run prisma generate`
4. `poetry run uvicorn app.main:app --reload`



## Prisma
- `poetry run prisma generate` - Generate Prisma client
- `poetry run prisma db push` - Push schema to database
- `poetry run prisma db push --force` - Force push schema to database
- `poetry run prisma db push --preview-feature` - Enable preview features