from __future__ import annotations

import re
from pathlib import Path


def migration_sql() -> str:
    return (Path(__file__).parents[1] / "migrations" / "001_initial.sql").read_text(encoding="utf-8")


def table_block(sql: str, table_name: str) -> str:
    match = re.search(rf"CREATE TABLE IF NOT EXISTS {table_name} \((.*?)\n\);", sql, re.DOTALL)
    assert match is not None, f"missing {table_name} table"
    return match.group(1)


def constraint_block(sql: str, constraint_name: str) -> str:
    match = re.search(
        rf"DO \$\$\nBEGIN\n  IF NOT EXISTS \((?:(?!END \$\$;).)*?ADD CONSTRAINT {constraint_name}(?:(?!END \$\$;).)*?END \$\$;",
        sql,
        re.DOTALL,
    )
    assert match is not None, f"missing {constraint_name} constraint block"
    return match.group(0)


def test_initial_migration_includes_production_persistence_schema():
    sql = migration_sql()

    assert "CREATE TABLE IF NOT EXISTS auth_users" in sql
    assert "CREATE TABLE IF NOT EXISTS auth_sessions" in sql
    assert "CREATE TABLE IF NOT EXISTS favorite_products" in sql
    assert "idx_favorite_products_user_created" in sql
    assert "uq_favorite_products_user_product_marketplace" in sql
    assert "idx_saved_looks_unique_user_task" in sql
    assert "auth_sessions_user_id_fkey" in sql
    assert "style_tasks_user_id_fkey" in sql
    assert "saved_looks_user_id_fkey" in sql


def test_saved_looks_outfit_is_nullable():
    saved_looks = table_block(migration_sql(), "saved_looks")

    assert "outfit JSONB" in saved_looks
    assert "outfit JSONB NOT NULL" not in saved_looks


def test_foreign_key_idempotency_checks_are_scoped_to_target_tables():
    sql = migration_sql()

    assert "conrelid = 'auth_sessions'::regclass" in constraint_block(sql, "auth_sessions_user_id_fkey")
    assert "conrelid = 'style_tasks'::regclass" in constraint_block(sql, "style_tasks_user_id_fkey")
    assert "conrelid = 'saved_looks'::regclass" in constraint_block(sql, "saved_looks_user_id_fkey")


def test_legacy_table_foreign_keys_are_added_without_validating_existing_rows():
    sql = migration_sql()

    assert "ON DELETE SET NULL NOT VALID;" in constraint_block(sql, "style_tasks_user_id_fkey")
    assert "ON DELETE CASCADE NOT VALID;" in constraint_block(sql, "saved_looks_user_id_fkey")
