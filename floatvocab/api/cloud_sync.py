from __future__ import annotations

import json
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import app as legacy_app


SYNC_TABLES = [
    "lexicons",
    "words",
    "plans",
    "reviews",
    "daily_stats",
    "user_profile",
    "app_settings",
]


class CloudSyncError(RuntimeError):
    pass


def _read_env(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


class SupabaseCloudSync:
    def __init__(self, db, *, repo_root: Path = legacy_app.APP_ROOT):
        self.db = db
        self.repo_root = repo_root
        self.env = _read_env(repo_root / ".env.supabase.local")
        self.supabase_url = (self.env.get("SUPABASE_URL") or self.env.get("NEXT_PUBLIC_SUPABASE_URL") or "").rstrip("/")
        self.anon_key = self.env.get("SUPABASE_ANON_KEY") or self.env.get("NEXT_PUBLIC_SUPABASE_ANON_KEY") or ""
        self.session_path = legacy_app.get_user_data_dir() / "supabase_session.json"

    def configured(self) -> bool:
        return bool(self.supabase_url and self.anon_key)

    def config_status(self) -> dict[str, Any]:
        return {
            "configured": self.configured(),
            "url_host": self.supabase_url.replace("https://", "").replace("http://", "") if self.supabase_url else "",
            "has_session": self.session_path.exists(),
        }

    def session(self) -> dict[str, Any] | None:
        if not self.session_path.exists():
            return None
        try:
            return json.loads(self.session_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

    def save_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.session_path.parent.mkdir(parents=True, exist_ok=True)
        user = payload.get("user") or {}
        session = {
            "access_token": payload.get("access_token", ""),
            "refresh_token": payload.get("refresh_token", ""),
            "expires_at": payload.get("expires_at"),
            "user": {
                "id": user.get("id", ""),
                "email": user.get("email", ""),
            },
        }
        self.session_path.write_text(json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8")
        return session

    def clear_session(self) -> None:
        if self.session_path.exists():
            self.session_path.unlink()

    def _request(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        body: Any | None = None,
        prefer: str | None = None,
    ) -> Any:
        if not self.configured():
            raise CloudSyncError("Supabase is not configured. Fill .env.supabase.local first.")
        headers = {
            "apikey": self.anon_key,
            "Authorization": f"Bearer {token or self.anon_key}",
            "Content-Type": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer
        data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(f"{self.supabase_url}{path}", data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                text = response.read().decode("utf-8")
                return json.loads(text) if text else None
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8", errors="replace")
            raise CloudSyncError(text or f"Supabase request failed with {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise CloudSyncError(str(exc.reason)) from exc

    def _require_session(self) -> dict[str, Any]:
        session = self.session()
        if not session or not session.get("access_token") or not session.get("user", {}).get("id"):
            raise CloudSyncError("Not logged in to FloatVocab cloud.")
        expires_at = session.get("expires_at")
        if expires_at and float(expires_at) - datetime.now(timezone.utc).timestamp() < 60 and session.get("refresh_token"):
            refreshed = self._request(
                "POST",
                "/auth/v1/token?grant_type=refresh_token",
                body={"refresh_token": session["refresh_token"]},
            )
            session = self.save_session(refreshed)
        return session

    def sign_up(self, email: str, password: str) -> dict[str, Any]:
        payload = self._request("POST", "/auth/v1/signup", body={"email": email, "password": password})
        if payload and payload.get("access_token"):
            return self.save_session(payload)
        return {"user": payload.get("user") if payload else None, "needs_confirmation": True}

    def login(self, email: str, password: str) -> dict[str, Any]:
        payload = self._request("POST", "/auth/v1/token?grant_type=password", body={"email": email, "password": password})
        return self.save_session(payload)

    def current_user(self) -> dict[str, Any] | None:
        session = self.session()
        if not session:
            return None
        return session.get("user")

    def local_summary(self) -> dict[str, Any]:
        conn = self.db.conn
        summary = {}
        for table in SYNC_TABLES:
            row = conn.execute(f"SELECT COUNT(*) AS total FROM {table}").fetchone()
            summary[f"{table}_count"] = int(row["total"] or 0)
        latest_candidates = []
        for query in [
            "SELECT MAX(updated_at) AS latest FROM words",
            "SELECT MAX(updated_at) AS latest FROM plans",
            "SELECT MAX(updated_at) AS latest FROM user_profile",
            "SELECT MAX(updated_at) AS latest FROM app_settings",
            "SELECT MAX(reviewed_at) AS latest FROM reviews",
            "SELECT MAX(day) AS latest FROM daily_stats",
        ]:
            row = conn.execute(query).fetchone()
            if row["latest"]:
                latest_candidates.append(str(row["latest"]))
        summary["latest_local_change"] = max(latest_candidates) if latest_candidates else None
        return summary

    def export_snapshot(self) -> dict[str, Any]:
        conn = self.db.conn
        data = {}
        for table in SYNC_TABLES:
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()
            data[table] = [_row_to_dict(row) for row in rows]
        return {
            "version": 1,
            "exported_at": _utc_now(),
            "summary": self.local_summary(),
            "tables": data,
        }

    def import_snapshot(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        tables = snapshot.get("tables")
        if not isinstance(tables, dict):
            raise CloudSyncError("Cloud snapshot is invalid.")
        conn = self.db.conn
        conn.commit()
        conn.execute("PRAGMA foreign_keys = OFF")
        try:
            for table in ["reviews", "daily_stats", "words", "plans", "user_profile", "app_settings", "lexicons"]:
                conn.execute(f"DELETE FROM {table}")
            for table in SYNC_TABLES:
                for row in tables.get(table, []):
                    if not row:
                        continue
                    columns = list(row.keys())
                    placeholders = ", ".join(["?"] * len(columns))
                    column_sql = ", ".join(columns)
                    conn.execute(
                        f"INSERT OR REPLACE INTO {table} ({column_sql}) VALUES ({placeholders})",
                        [row[column] for column in columns],
                    )
            conn.commit()
        finally:
            conn.execute("PRAGMA foreign_keys = ON")
        return self.local_summary()

    def remote_state(self) -> dict[str, Any] | None:
        session = self._require_session()
        user_id = session["user"]["id"]
        rows = self._request(
            "GET",
            f"/rest/v1/floatvocab_sync_state?select=user_id,client_updated_at,updated_at&user_id=eq.{user_id}&limit=1",
            token=session["access_token"],
        )
        return rows[0] if rows else None

    def upload(self) -> dict[str, Any]:
        session = self._require_session()
        user_id = session["user"]["id"]
        snapshot = self.export_snapshot()
        rows = self._request(
            "POST",
            "/rest/v1/floatvocab_sync_state",
            token=session["access_token"],
            prefer="resolution=merge-duplicates,return=representation",
            body={
                "user_id": user_id,
                "data": snapshot,
                "client_updated_at": snapshot["exported_at"],
            },
        )
        return {"remote": rows[0] if rows else None, "summary": snapshot["summary"]}

    def download(self) -> dict[str, Any]:
        session = self._require_session()
        user_id = session["user"]["id"]
        rows = self._request(
            "GET",
            f"/rest/v1/floatvocab_sync_state?select=*&user_id=eq.{user_id}&limit=1",
            token=session["access_token"],
        )
        if not rows:
            raise CloudSyncError("No cloud snapshot exists for this account.")
        snapshot = rows[0].get("data") or {}
        return {"remote": rows[0], "summary": self.import_snapshot(snapshot)}
