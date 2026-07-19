from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[2] / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    gf_database_url: str = Field(
        default=f"sqlite+aiosqlite:///{(ROOT / 'data' / 'factory.db').as_posix()}",
        alias="GF_DATABASE_URL",
    )
    gf_data_dir: Path = Field(default=ROOT / "data", alias="GF_DATA_DIR")
    gf_skeletons_dir: Path = Field(default=ROOT / "skeletons", alias="GF_SKELETONS_DIR")
    gf_host: str = Field(default="127.0.0.1", alias="GF_HOST")
    gf_port: int = Field(default=8000, alias="GF_PORT")

    deepseek_api_key: str = Field(default="", alias="DEEPSEEK_API_KEY")
    deepseek_base_url: str = Field(default="https://api.deepseek.com", alias="DEEPSEEK_BASE_URL")
    deepseek_model: str = Field(default="deepseek-v4-flash", alias="DEEPSEEK_MODEL")

    # 登录氛围图（可选；无 key 时用领域兜底 Unsplash 直链）
    unsplash_access_key: str = Field(default="", alias="UNSPLASH_ACCESS_KEY")

    gf_backend_port_start: int = Field(default=9100, alias="GF_BACKEND_PORT_START")
    gf_backend_port_end: int = Field(default=9120, alias="GF_BACKEND_PORT_END")
    gf_frontend_port_start: int = Field(default=9200, alias="GF_FRONTEND_PORT_START")
    gf_frontend_port_end: int = Field(default=9220, alias="GF_FRONTEND_PORT_END")

    # 学生项目 MySQL（与工厂元数据库分离；对齐 docker-compose root）
    gf_student_mysql_host: str = Field(default="127.0.0.1", alias="GF_STUDENT_MYSQL_HOST")
    gf_student_mysql_port: int = Field(default=3306, alias="GF_STUDENT_MYSQL_PORT")
    gf_student_mysql_user: str = Field(default="root", alias="GF_STUDENT_MYSQL_USER")
    gf_student_mysql_password: str = Field(default="root123", alias="GF_STUDENT_MYSQL_PASSWORD")

    monthly_token_budget: int = 1_000_000
    project_token_budget: int = 100_000
    fix_rounds_max: int = 5

    @property
    def database_url(self) -> str:
        return self.gf_database_url

    @property
    def data_dir(self) -> Path:
        p = self.gf_data_dir
        return p if p.is_absolute() else (ROOT / p).resolve()

    @property
    def skeletons_dir(self) -> Path:
        p = self.gf_skeletons_dir
        return p if p.is_absolute() else (ROOT / p).resolve()

    @property
    def host(self) -> str:
        return self.gf_host

    @property
    def port(self) -> int:
        return self.gf_port

    @property
    def backend_port_start(self) -> int:
        return self.gf_backend_port_start

    @property
    def backend_port_end(self) -> int:
        return self.gf_backend_port_end

    @property
    def frontend_port_start(self) -> int:
        return self.gf_frontend_port_start

    @property
    def frontend_port_end(self) -> int:
        return self.gf_frontend_port_end

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def workspace_dir(self) -> Path:
        return self.data_dir / "workspace"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def cache_dir(self) -> Path:
        """共享缓存（如 baseline 前端 node_modules），避免每题重装依赖。"""
        return self.data_dir / "cache"


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    for p in (s.data_dir, s.uploads_dir, s.workspace_dir, s.logs_dir, s.cache_dir):
        p.mkdir(parents=True, exist_ok=True)
    return s
