# Database Migrations

This folder contains SQL migration scripts for updating the database schema in production.

## How Migrations Work

1. **Automatic**: When the app starts, `init_db()` in `database.py` automatically runs `migrate.py`
2. **Safe**: Migrations check if changes already exist before applying them
3. **Non-breaking**: Failed migrations log warnings but don't crash the app

## Migration Files

### 001_add_difficulty_column.sql
- **Date**: 2025-11-06
- **Purpose**: Adds `difficulty` column to `game_sessions` table
- **Values**: 'easy', 'medium' (default), 'hard'
- **Effect**: Controls starting resources for teams (±25%)

## Manual Migration (if needed)

If automatic migration fails, you can manually run SQL scripts against your Azure PostgreSQL database:

```bash
# Connect to Azure PostgreSQL
psql "postgresql://username:password@server.postgres.database.azure.com/dbname?sslmode=require"

# Run migration
\i backend/migrations/001_add_difficulty_column.sql
```

Or use Azure Portal Query Editor to paste and execute the SQL.

## Adding New Migrations

When adding new columns or tables:

1. Create a new SQL file: `00X_descriptive_name.sql`
2. Add migration to `migrate.py` migrations list
3. Test locally with both SQLite and PostgreSQL
4. Commit and deploy

## Troubleshooting

**Error: "column does not exist"**
- The migration hasn't run yet or failed
- Check app logs for migration errors
- Manually run the SQL script

**Error: "column already exists"**
- Migration already applied (safe to ignore)
- The code handles this gracefully
