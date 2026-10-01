"""SQLite Analysis History, User Authentication & Persistence Layer.

Stores actual completed AI clinical image analyses, users, roles, and artifact metadata.

Design Principles:
------------------
1. SQLite3 Standard Library: Zero-dependency, lightweight, reliable local persistence.
2. User Authentication & RBAC: Persistent users table with secure password hashes and roles (ADMIN, USER).
3. Analysis Ownership Isolation: Analyses are mapped to owner_user_id to ensure strict multi-tenant privacy.
4. Safe Parameterized Queries: 100% protection against SQL injection.
5. Migration-Ready: Automatic column/table migration for existing databases.
"""

import os
import sys
import json
import base64
import sqlite3
import logging
from uuid import uuid4
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Union

logger = logging.getLogger("Database")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Backend root directory
BACKEND_ROOT = Path(__file__).resolve().parent.parent


def get_default_db_path() -> Path:
    """Resolve database path from environment variable or standard backend data directory."""
    env_db = os.getenv("DATABASE_PATH") or os.getenv("SQLITE_DB_PATH")
    if env_db:
        return Path(env_db)
    return BACKEND_ROOT / "data" / "medical_ai.db"


get_db_path = get_default_db_path



def get_default_storage_dir() -> Path:
    """Resolve artifact storage directory for saved radiographs and visualizations."""
    env_storage = os.getenv("STORAGE_DIR")
    if env_storage:
        return Path(env_storage)
    return BACKEND_ROOT / "data" / "visualizations"


def get_db_connection(db_path: Optional[Union[str, Path]] = None) -> sqlite3.Connection:
    """Create and return an optimized SQLite database connection.

    Args:
        db_path: Path to SQLite database file. If None, uses default path.

    Returns:
        sqlite3.Connection with row_factory configured to sqlite3.Row.
    """
    target_path = Path(db_path) if db_path else get_default_db_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(
        str(target_path),
        timeout=30.0,
        detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
    )
    conn.row_factory = sqlite3.Row

    # Performance and concurrency pragmas for SQLite
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def initialize_database(db_path: Optional[Union[str, Path]] = None) -> None:
    """Initialize SQLite database schema, user accounts table, and indexes."""
    target_path = Path(db_path) if db_path else get_default_db_path()
    logger.info(f"Initializing SQLite database at: {target_path}")

    conn = get_db_connection(target_path)
    try:
        with conn:
            # 1. Users Table (Authentication, Anonymous Secure Tokens & RBAC)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE,
                    password_hash TEXT,
                    role TEXT NOT NULL DEFAULT 'USER',
                    token_hash TEXT UNIQUE,
                    token_expires_at TEXT,
                    created_at TEXT NOT NULL,
                    last_seen_at TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1
                );
                """
            )
            # Check and run migrations for users table columns first
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(users);")
            user_columns = [row["name"] for row in cursor.fetchall()]
            if "token_hash" not in user_columns:
                logger.info("Migrating users table: adding token_hash column...")
                conn.execute("ALTER TABLE users ADD COLUMN token_hash TEXT;")
            if "token_expires_at" not in user_columns:
                logger.info("Migrating users table: adding token_expires_at column...")
                conn.execute("ALTER TABLE users ADD COLUMN token_expires_at TEXT;")
            if "last_seen_at" not in user_columns:
                logger.info("Migrating users table: adding last_seen_at column...")
                conn.execute("ALTER TABLE users ADD COLUMN last_seen_at TEXT;")

            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);")
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_token_hash ON users(token_hash);")

            # 2. Analyses Table (Clinical Records)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_id TEXT UNIQUE NOT NULL,
                    owner_user_id TEXT,
                    created_at TEXT NOT NULL,
                    filename TEXT,
                    prediction TEXT NOT NULL,
                    predicted_index INTEGER NOT NULL,
                    confidence REAL NOT NULL,
                    probabilities_json TEXT NOT NULL,
                    model_version TEXT NOT NULL,
                    architecture TEXT NOT NULL,
                    device TEXT NOT NULL,
                    inference_time_ms REAL NOT NULL,
                    target_class TEXT NOT NULL,
                    image_reference TEXT,
                    heatmap_reference TEXT,
                    overlay_reference TEXT,
                    original_dimensions_json TEXT,
                    status TEXT DEFAULT 'completed'
                );
                """
            )

            # Check and run migrations if owner_user_id is missing in existing table
            cursor.execute("PRAGMA table_info(analyses);")
            columns = [row["name"] for row in cursor.fetchall()]
            if "owner_user_id" not in columns:
                logger.info("Migrating analyses table: adding owner_user_id column...")
                conn.execute("ALTER TABLE analyses ADD COLUMN owner_user_id TEXT;")

            # Indexing for rapid query retrieval and history pagination
            conn.execute("CREATE INDEX IF NOT EXISTS idx_analyses_analysis_id ON analyses(analysis_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_analyses_owner ON analyses(owner_user_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_analyses_created_at ON analyses(created_at DESC);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_analyses_prediction ON analyses(prediction);")

            # 3. Prescriptions Table (Task 25 & 26 Prescription Understanding Records)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS prescriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_id TEXT UNIQUE NOT NULL,
                    owner_user_id TEXT,
                    created_at TEXT NOT NULL,
                    filename TEXT,
                    total_medications INTEGER NOT NULL DEFAULT 0,
                    status TEXT DEFAULT 'completed',
                    result_json TEXT NOT NULL,
                    image_reference TEXT,
                    processing_time_ms REAL NOT NULL DEFAULT 0.0
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_prescriptions_id ON prescriptions(analysis_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_prescriptions_owner ON prescriptions(owner_user_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_prescriptions_created_at ON prescriptions(created_at DESC);")

        logger.info("SQLite database schema initialized successfully.")
    finally:
        conn.close()


# -----------------------------------------------------------------------------
# User Management & Authentication Helpers
# -----------------------------------------------------------------------------

def create_anonymous_user(
    token_hash: str,
    expires_at: Optional[datetime] = None,
    user_id: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Create a new anonymous USER record with a cryptographically hashed token."""
    uid = user_id or str(uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()
    expires_iso = expires_at.isoformat() if expires_at else None
    anon_username = f"anon_{uid[:8]}"

    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO users (id, username, password_hash, role, token_hash, token_expires_at, created_at, last_seen_at, is_active)
                VALUES (?, ?, '$anonymous$', 'USER', ?, ?, ?, ?, 1);
                """,
                (uid, anon_username, token_hash, expires_iso, now_iso, now_iso),
            )
        return {
            "id": uid,
            "username": anon_username,
            "role": "USER",
            "token_hash": token_hash,
            "token_expires_at": expires_iso,
            "created_at": now_iso,
            "last_seen_at": now_iso,
            "is_active": True,
        }
    finally:
        conn.close()


def get_user_by_token_hash(
    token_hash: str,
    db_path: Optional[Union[str, Path]] = None,
) -> Optional[Dict[str, Any]]:
    """Look up an active user record by SHA-256 token hash."""
    if not token_hash:
        return None
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE token_hash = ? AND is_active = 1 LIMIT 1;",
            (token_hash,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        d["is_active"] = bool(d.get("is_active", 1))
        return d
    finally:
        conn.close()


def update_user_last_seen(
    user_id: str,
    db_path: Optional[Union[str, Path]] = None,
) -> None:
    """Update the last_seen_at timestamp for a user session."""
    now_iso = datetime.now(timezone.utc).isoformat()
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute(
                "UPDATE users SET last_seen_at = ? WHERE id = ?;",
                (now_iso, user_id),
            )
    except Exception as e:
        logger.debug(f"Failed to update last_seen_at: {e}")
    finally:
        conn.close()


def invalidate_user_token(
    user_id: str,
    db_path: Optional[Union[str, Path]] = None,
) -> None:
    """Invalidate an active user's session token."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute(
                "UPDATE users SET token_hash = NULL, token_expires_at = NULL WHERE id = ?;",
                (user_id,),
            )
    finally:
        conn.close()


def rotate_user_token(
    user_id: str,
    new_token_hash: str,
    expires_at: Optional[datetime] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> None:
    """Rotate an existing user session token without changing their identity or history."""
    expires_iso = expires_at.isoformat() if expires_at else None
    now_iso = datetime.now(timezone.utc).isoformat()
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                UPDATE users
                SET token_hash = ?, token_expires_at = ?, last_seen_at = ?
                WHERE id = ?;
                """,
                (new_token_hash, expires_iso, now_iso, user_id),
            )
    finally:
        conn.close()


def create_user(
    username: str,
    password_hash: Optional[str] = None,
    role: str = "USER",
    is_active: bool = True,
    user_id: Optional[str] = None,
    token_hash: Optional[str] = None,
    token_expires_at: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Create a new user in the SQLite database."""
    uid = user_id or str(uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()
    clean_username = username.strip().lower()
    clean_role = role.strip().upper() if role.strip().upper() in ["ADMIN", "USER"] else "USER"

    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO users (id, username, password_hash, role, token_hash, token_expires_at, is_active, created_at, last_seen_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (uid, clean_username, password_hash, clean_role, token_hash, token_expires_at, 1 if is_active else 0, now_iso, now_iso),
            )
        return {
            "id": uid,
            "username": clean_username,
            "role": clean_role,
            "is_active": is_active,
            "created_at": now_iso,
            "last_seen_at": now_iso,
        }
    finally:
        conn.close()


def get_user_by_username(
    username: str,
    db_path: Optional[Union[str, Path]] = None,
) -> Optional[Dict[str, Any]]:
    """Look up a user record by username (case-insensitive)."""
    clean_username = username.strip().lower()
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE username = ? LIMIT 1;",
            (clean_username,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        d["is_active"] = bool(d.get("is_active", 1))
        return d
    finally:
        conn.close()


def get_user_by_id(
    user_id: str,
    db_path: Optional[Union[str, Path]] = None,
) -> Optional[Dict[str, Any]]:
    """Look up a user record by user UUID."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE id = ? LIMIT 1;",
            (user_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        d["is_active"] = bool(d.get("is_active", 1))
        return d
    finally:
        conn.close()


def list_users(
    limit: int = 100,
    offset: int = 0,
    db_path: Optional[Union[str, Path]] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """List registered users with pagination (excluding password hashes)."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users;")
        total = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT id, username, role, is_active, created_at
            FROM users
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?;
            """,
            (limit, offset),
        )
        rows = cursor.fetchall()
        users = []
        for r in rows:
            u = dict(r)
            u["is_active"] = bool(u.get("is_active", 1))
            users.append(u)
        return users, total
    finally:
        conn.close()


def count_users(db_path: Optional[Union[str, Path]] = None) -> int:
    """Return total count of registered users."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users;")
        return cursor.fetchone()[0]
    finally:
        conn.close()


def update_user_status(
    user_id: str,
    is_active: bool,
    db_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Update active/suspended status of a user account and return updated record."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute(
                "UPDATE users SET is_active = ? WHERE id = ?;",
                (1 if is_active else 0, user_id),
            )
        updated = get_user_by_id(user_id, db_path=db_path)
        return updated if updated else {"id": user_id, "is_active": is_active}
    finally:
        conn.close()


def seed_admin_user(
    username: Optional[str] = None,
    password_hash: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Seed initial ADMIN user account if not already present."""
    from api.auth import hash_password
    admin_user = username or os.getenv("ADMIN_USERNAME") or "admin"
    existing = get_user_by_username(admin_user, db_path=db_path)
    if existing:
        return existing

    if password_hash:
        hashed = password_hash
    else:
        raw_pass = os.getenv("ADMIN_PASSWORD") or "AdminSecure2026!Clinical"
        hashed = hash_password(raw_pass)

    return create_user(
        username=admin_user,
        password_hash=hashed,
        role="ADMIN",
        is_active=True,
        db_path=db_path,
    )



# -----------------------------------------------------------------------------
# Analysis Storage & Retrieval Helpers
# -----------------------------------------------------------------------------

def save_analysis_artifacts(
    analysis_id: str,
    original_bytes: bytes,
    original_filename: Optional[str] = None,
    heatmap_base64: Optional[str] = None,
    overlay_base64: Optional[str] = None,
    storage_dir: Optional[Union[str, Path]] = None,
) -> Dict[str, Optional[str]]:
    """Safely persist image artifacts to disk and return relative safe references."""
    base_dir = Path(storage_dir) if storage_dir else get_default_storage_dir()
    analysis_dir = base_dir / analysis_id
    analysis_dir.mkdir(parents=True, exist_ok=True)

    # Determine safe file extension
    ext = ".png"
    if original_filename:
        user_ext = Path(original_filename).suffix.lower()
        if user_ext in [".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"]:
            ext = user_ext

    # 1. Save original radiograph
    orig_path = analysis_dir / f"original{ext}"
    orig_path.write_bytes(original_bytes)
    orig_ref = f"{analysis_id}/original{ext}"

    # 2. Save Grad-CAM heatmap if present
    heat_ref = None
    if heatmap_base64 and "," in heatmap_base64:
        try:
            heat_bytes = base64.b64decode(heatmap_base64.split(",", 1)[1])
            heat_path = analysis_dir / "gradcam_heatmap.png"
            heat_path.write_bytes(heat_bytes)
            heat_ref = f"{analysis_id}/gradcam_heatmap.png"
        except Exception as e:
            logger.warning(f"Failed to persist heatmap artifact: {e}")

    # 3. Save Grad-CAM overlay if present
    over_ref = None
    if overlay_base64 and "," in overlay_base64:
        try:
            over_bytes = base64.b64decode(overlay_base64.split(",", 1)[1])
            over_path = analysis_dir / "gradcam_overlay.png"
            over_path.write_bytes(over_bytes)
            over_ref = f"{analysis_id}/gradcam_overlay.png"
        except Exception as e:
            logger.warning(f"Failed to persist overlay artifact: {e}")

    return {
        "image_reference": orig_ref,
        "heatmap_reference": heat_ref,
        "overlay_reference": over_ref,
    }


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """Convert an SQLite Row into a cleanly structured Python dictionary."""
    d = dict(row)
    # Parse JSON fields safely
    if "probabilities_json" in d and isinstance(d["probabilities_json"], str):
        try:
            d["probabilities"] = json.loads(d["probabilities_json"])
        except Exception:
            d["probabilities"] = {}
        del d["probabilities_json"]

    if "original_dimensions_json" in d and isinstance(d["original_dimensions_json"], str):
        try:
            d["original_dimensions"] = json.loads(d["original_dimensions_json"])
        except Exception:
            d["original_dimensions"] = None
        del d["original_dimensions_json"]

    return d


def create_analysis(
    data: Dict[str, Any],
    db_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Insert a completed clinical analysis record into SQLite with ownership."""
    analysis_id = data.get("analysis_id") or str(uuid4())
    owner_user_id = data.get("owner_user_id")
    created_at = data.get("created_at") or datetime.now(timezone.utc).isoformat()

    filename = data.get("filename")
    prediction = data["prediction"]
    predicted_index = int(data.get("predicted_index", 0 if prediction == "NORMAL" else 1))
    confidence = float(data["confidence"])
    probabilities = data.get("probabilities", {})
    probabilities_json = json.dumps(probabilities)
    model_version = str(data.get("model_version", "1.0.0"))
    architecture = str(data.get("architecture", "resnet18"))
    device = str(data.get("device", "cpu"))
    inference_time_ms = float(data.get("inference_time_ms", 0.0))
    target_class = str(data.get("target_class", prediction))
    image_reference = data.get("image_reference")
    heatmap_reference = data.get("heatmap_reference")
    overlay_reference = data.get("overlay_reference")
    original_dimensions = data.get("original_dimensions")
    original_dimensions_json = json.dumps(original_dimensions) if original_dimensions else None
    status_val = data.get("status", "completed")

    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO analyses (
                    analysis_id, owner_user_id, created_at, filename, prediction, predicted_index,
                    confidence, probabilities_json, model_version, architecture,
                    device, inference_time_ms, target_class, image_reference,
                    heatmap_reference, overlay_reference, original_dimensions_json, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    analysis_id,
                    owner_user_id,
                    created_at,
                    filename,
                    prediction,
                    predicted_index,
                    confidence,
                    probabilities_json,
                    model_version,
                    architecture,
                    device,
                    inference_time_ms,
                    target_class,
                    image_reference,
                    heatmap_reference,
                    overlay_reference,
                    original_dimensions_json,
                    status_val,
                ),
            )
    finally:
        conn.close()

    return {
        "analysis_id": analysis_id,
        "owner_user_id": owner_user_id,
        "created_at": created_at,
        "filename": filename,
        "prediction": prediction,
        "predicted_index": predicted_index,
        "confidence": round(confidence, 4),
        "probabilities": probabilities,
        "model_version": model_version,
        "architecture": architecture,
        "device": device,
        "inference_time_ms": round(inference_time_ms, 2),
        "target_class": target_class,
        "image_reference": image_reference,
        "heatmap_reference": heatmap_reference,
        "overlay_reference": overlay_reference,
        "original_dimensions": original_dimensions,
        "status": status_val,
    }


def get_analysis_by_id(
    analysis_id: str,
    db_path: Optional[Union[str, Path]] = None,
) -> Optional[Dict[str, Any]]:
    """Retrieve a single stored analysis record by its unique UUID."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM analyses WHERE analysis_id = ? LIMIT 1;",
            (analysis_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return row_to_dict(row)
    finally:
        conn.close()


def get_analysis_history(
    limit: int = 50,
    offset: int = 0,
    owner_user_id: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """Retrieve paginated analysis records ordered by newest first.

    Args:
        limit: Maximum number of records to return.
        offset: Number of records to skip.
        owner_user_id: If provided, filters records exclusively to this owner. If None (ADMIN), returns all.
        db_path: Target SQLite database file.

    Returns:
        Tuple of (List of analysis dicts, Total count of matching records).
    """
    safe_limit = max(1, min(limit, 100))
    safe_offset = max(0, offset)

    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        if owner_user_id is not None:
            cursor.execute("SELECT COUNT(*) FROM analyses WHERE owner_user_id = ?;", (owner_user_id,))
            total = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT * FROM analyses
                WHERE owner_user_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ? OFFSET ?;
                """,
                (owner_user_id, safe_limit, safe_offset),
            )
        else:
            cursor.execute("SELECT COUNT(*) FROM analyses;")
            total = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT * FROM analyses
                ORDER BY created_at DESC, id DESC
                LIMIT ? OFFSET ?;
                """,
                (safe_limit, safe_offset),
            )

        rows = cursor.fetchall()
        items = [row_to_dict(row) for row in rows]
        return items, total
    finally:
        conn.close()


def count_analyses(
    owner_user_id: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Return total count of analyses (optionally filtered by owner)."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        if owner_user_id is not None:
            cursor.execute("SELECT COUNT(*) FROM analyses WHERE owner_user_id = ?;", (owner_user_id,))
        else:
            cursor.execute("SELECT COUNT(*) FROM analyses;")
        return cursor.fetchone()[0]
    finally:
        conn.close()


def get_admin_statistics(db_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """Compute aggregate administrative statistics across all platform analyses."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM analyses;")
        total_analyses = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM analyses WHERE prediction = 'NORMAL';")
        total_normal = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM analyses WHERE prediction = 'PNEUMONIA';")
        total_pneumonia = cursor.fetchone()[0]

        cursor.execute("SELECT AVG(confidence), AVG(inference_time_ms) FROM analyses;")
        avg_row = cursor.fetchone()
        avg_confidence = round(avg_row[0], 4) if avg_row and avg_row[0] is not None else 0.0
        avg_latency = round(avg_row[1], 2) if avg_row and avg_row[1] is not None else 0.0

        cursor.execute("SELECT COUNT(*) FROM users;")
        total_users = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1;")
        active_users = cursor.fetchone()[0]

        return {
            "total_analyses": total_analyses,
            "total_normal": total_normal,
            "total_pneumonia": total_pneumonia,
            "average_confidence": avg_confidence,
            "average_inference_time_ms": avg_latency,
            "total_users": total_users,
            "active_users": active_users,
        }
    finally:
        conn.close()


def delete_analysis(
    analysis_id: str,
    db_path: Optional[Union[str, Path]] = None,
) -> bool:
    """Delete an analysis record by its unique UUID."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            cursor = conn.execute(
                "DELETE FROM analyses WHERE analysis_id = ?;",
                (analysis_id,),
            )
            return cursor.rowcount > 0
    finally:
        conn.close()


# -----------------------------------------------------------------------------
# Prescription Persistence & Artifact Helpers (Task 25 & 26)
# -----------------------------------------------------------------------------

def save_prescription_artifacts(
    analysis_id: str,
    original_bytes: bytes,
    original_filename: Optional[str] = None,
    storage_dir: Optional[Union[str, Path]] = None,
) -> Dict[str, str]:
    """Persist uploaded prescription image artifact securely to disk."""
    base_dir = Path(storage_dir) if storage_dir else get_default_storage_dir()
    analysis_dir = base_dir / analysis_id
    analysis_dir.mkdir(parents=True, exist_ok=True)

    ext = ".jpg"
    if original_filename and "." in original_filename:
        safe_ext = "." + original_filename.rsplit(".", 1)[1].lower()
        if safe_ext in [".png", ".jpg", ".jpeg", ".webp"]:
            ext = safe_ext

    orig_path = analysis_dir / f"prescription_original{ext}"
    orig_path.write_bytes(original_bytes)
    orig_ref = f"{analysis_id}/prescription_original{ext}"

    return {
        "image_reference": orig_ref,
    }


def create_prescription_analysis(
    data: Dict[str, Any],
    db_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Insert a completed prescription understanding record into SQLite with ownership."""
    analysis_id = data.get("analysis_id") or str(uuid4())
    owner_user_id = data.get("owner_user_id")
    created_at = data.get("created_at") or datetime.now(timezone.utc).isoformat()
    filename = data.get("filename")
    total_medications = int(data.get("total_medications", 0))
    status_val = data.get("status", "completed")
    processing_time_ms = float(data.get("processing_time_ms", 0.0))
    image_reference = data.get("image_reference")
    
    result_data = data.get("result", {})
    if isinstance(result_data, dict):
        result_json = json.dumps(result_data)
    elif isinstance(result_data, str):
        result_json = result_data
    else:
        result_json = "{}"

    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO prescriptions (
                    analysis_id, owner_user_id, created_at, filename,
                    total_medications, status, result_json, image_reference, processing_time_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    analysis_id,
                    owner_user_id,
                    created_at,
                    filename,
                    total_medications,
                    status_val,
                    result_json,
                    image_reference,
                    processing_time_ms,
                ),
            )
        return {
            "analysis_id": analysis_id,
            "owner_user_id": owner_user_id,
            "created_at": created_at,
            "filename": filename,
            "total_medications": total_medications,
            "status": status_val,
            "image_reference": image_reference,
            "processing_time_ms": processing_time_ms,
            "result": result_data if isinstance(result_data, dict) else json.loads(result_json),
        }
    finally:
        conn.close()


def get_prescription_analysis_by_id(
    analysis_id: str,
    db_path: Optional[Union[str, Path]] = None,
) -> Optional[Dict[str, Any]]:
    """Retrieve a single prescription record by its unique UUID."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM prescriptions WHERE analysis_id = ? LIMIT 1;", (analysis_id,))
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        if "analysis_id" in d:
            d["id"] = d["analysis_id"]
        if "result_json" in d and isinstance(d["result_json"], str):
            try:
                d["result"] = json.loads(d["result_json"])
            except Exception:
                d["result"] = {}
            del d["result_json"]
        return d
    finally:
        conn.close()


def get_prescription_history(
    limit: int = 50,
    offset: int = 0,
    owner_user_id: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """Retrieve paginated prescription history records ordered newest first."""
    safe_limit = max(1, min(limit, 100))
    safe_offset = max(0, offset)

    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        if owner_user_id is not None:
            cursor.execute("SELECT COUNT(*) FROM prescriptions WHERE owner_user_id = ?;", (owner_user_id,))
            total = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT * FROM prescriptions
                WHERE owner_user_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ? OFFSET ?;
                """,
                (owner_user_id, safe_limit, safe_offset),
            )
        else:
            cursor.execute("SELECT COUNT(*) FROM prescriptions;")
            total = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT * FROM prescriptions
                ORDER BY created_at DESC, id DESC
                LIMIT ? OFFSET ?;
                """,
                (safe_limit, safe_offset),
            )

        rows = cursor.fetchall()
        items = []
        for r in rows:
            d = dict(r)
            if "analysis_id" in d:
                d["id"] = d["analysis_id"]
            if "result_json" in d and isinstance(d["result_json"], str):
                try:
                    d["result"] = json.loads(d["result_json"])
                except Exception:
                    d["result"] = {}
                del d["result_json"]
            items.append(d)
        return items, total
    finally:
        conn.close()


def count_prescription_analyses(
    owner_user_id: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Return total count of prescription analyses (optionally filtered by owner)."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        if owner_user_id is not None:
            cursor.execute("SELECT COUNT(*) FROM prescriptions WHERE owner_user_id = ?;", (owner_user_id,))
        else:
            cursor.execute("SELECT COUNT(*) FROM prescriptions;")
        return cursor.fetchone()[0]
    finally:
        conn.close()

