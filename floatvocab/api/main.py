from __future__ import annotations

import sqlite3
from contextlib import asynccontextmanager
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import app as legacy_app
from floatvocab.services import NewsService, SettingsService, StudyService


class ReviewPayload(BaseModel):
    word_id: int = Field(gt=0)
    rating: int = Field(ge=1, le=5)


class PlanPayload(BaseModel):
    lexicon_id: int = Field(gt=0)
    daily_new: int = Field(gt=0)
    target_date: str
    float_alpha: float = Field(ge=0.35, le=1.0)
    font_size: int = Field(ge=16, le=56)
    bg_color: str
    widget_size: str
    current_language_code: str | None = None


class FloatStylePayload(BaseModel):
    float_alpha: float = Field(ge=0.35, le=1.0)
    font_size: int = Field(ge=16, le=56)
    bg_color: str
    widget_size: str


class GlobalTranslationPayload(BaseModel):
    enabled: bool


class UserProfilePayload(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)
    avatar_url: str = ""
    bio: str = ""


class AppSettingsPayload(BaseModel):
    theme: str = "light"
    default_window_width: int = Field(ge=900)
    default_window_height: int = Field(ge=600)
    launch_at_startup: bool = False


def to_jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, sqlite3.Row):
        return {key: to_jsonable(value[key]) for key in value.keys()}
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    return value


class ApiContext:
    def __init__(self, db_path: Path):
        self.db = legacy_app.FloatVocabDB(db_path)
        self.study_service = StudyService(self.db)
        self.settings_service = SettingsService(self.db)
        self.news_service = NewsService(db_path)

    def close(self) -> None:
        self.db.conn.close()


@asynccontextmanager
async def lifespan(api: FastAPI):
    api.state.context = ApiContext(legacy_app.DB_PATH)
    try:
        yield
    finally:
        api.state.context.close()


app = FastAPI(title="FloatVocab API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "app://floatvocab", "file://", "null"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def context() -> ApiContext:
    return app.state.context


@app.get("/health")
async def health():
    return {"ok": True, "app": "FloatVocab"}


@app.get("/plan")
async def get_plan():
    return to_jsonable(context().settings_service.get_plan_settings())


@app.put("/plan")
async def save_plan(payload: PlanPayload):
    try:
        context().settings_service.save_plan(
            payload.lexicon_id,
            payload.daily_new,
            payload.target_date,
            payload.float_alpha,
            payload.font_size,
            payload.bg_color,
            payload.widget_size,
            current_language_code=payload.current_language_code,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return to_jsonable(context().settings_service.get_plan_settings())


@app.put("/plan/float-style")
async def save_float_style(payload: FloatStylePayload):
    context().settings_service.save_float_style(
        payload.float_alpha,
        payload.font_size,
        payload.bg_color,
        payload.widget_size,
    )
    return to_jsonable(context().settings_service.get_plan_settings())


@app.put("/plan/global-translation")
async def set_global_translation(payload: GlobalTranslationPayload):
    context().settings_service.set_global_translation_enabled(payload.enabled)
    return to_jsonable(context().settings_service.get_plan_settings())


@app.get("/profile")
async def get_profile():
    return to_jsonable(context().settings_service.get_user_profile())


@app.put("/profile")
async def save_profile(payload: UserProfilePayload):
    try:
        return to_jsonable(
            context().settings_service.save_user_profile(
                payload.display_name,
                payload.avatar_url,
                payload.bio,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/app-settings")
async def get_app_settings():
    return to_jsonable(context().settings_service.get_app_settings())


@app.put("/app-settings")
async def save_app_settings(payload: AppSettingsPayload):
    try:
        return to_jsonable(
            context().settings_service.save_app_settings(
                theme=payload.theme,
                default_window_width=payload.default_window_width,
                default_window_height=payload.default_window_height,
                launch_at_startup=payload.launch_at_startup,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/languages")
async def list_languages():
    return [{"code": code, "label": label} for code, label in context().settings_service.list_supported_languages()]


@app.get("/lexicons")
async def list_lexicons(language_code: str | None = None):
    plan = context().settings_service.get_plan_settings()
    active_language = language_code or plan["current_language_code"]
    return to_jsonable(context().db.lexicons(active_language))


@app.get("/cards/next")
async def next_card():
    return to_jsonable(context().study_service.get_next_card())


@app.post("/reviews")
async def submit_review(payload: ReviewPayload):
    context().study_service.submit_review(payload.word_id, payload.rating)
    return {
        "ok": True,
        "next_card": to_jsonable(context().study_service.get_next_card()),
        "stats": to_jsonable(context().study_service.get_study_stats()),
    }


@app.get("/stats")
async def get_stats():
    return to_jsonable(context().study_service.get_study_stats())


@app.get("/words/recent")
async def recent_words(lexicon_id: int, limit: int = 80):
    return to_jsonable(context().study_service.get_recent_words(lexicon_id, limit))


@app.get("/news/latest")
async def latest_news(language_code: str | None = None, limit: int = 10):
    return to_jsonable(context().news_service.list_latest_briefs(language_code, limit))


@app.post("/news/latest/refresh")
async def refresh_news(language_code: str | None = None, limit: int = 10):
    return to_jsonable(context().news_service.refresh_latest_briefs(language_code, limit))


@app.get("/news/favorites")
async def favorite_news(language_code: str | None = None):
    return to_jsonable(context().news_service.list_favorite_articles(language_code))
