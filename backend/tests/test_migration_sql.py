from __future__ import annotations

from pathlib import Path


def test_initial_migration_includes_production_persistence_schema():
    sql = (Path(__file__).parents[1] / "migrations" / "001_initial.sql").read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS auth_users" in sql
    assert "CREATE TABLE IF NOT EXISTS auth_sessions" in sql
    assert "CREATE TABLE IF NOT EXISTS favorite_products" in sql
    assert "idx_favorite_products_user_created" in sql
    assert "uq_favorite_products_user_product_marketplace" in sql
    assert "idx_saved_looks_unique_user_task" in sql
    assert "auth_sessions_user_id_fkey" in sql
    assert "style_tasks_user_id_fkey" in sql
    assert "saved_looks_user_id_fkey" in sql
