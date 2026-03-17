from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


class AppSettings(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    log_level: str = "INFO"
    loki_url: str = (
        ""  # ex: "http://localhost:3100/loki/api/v1/push" — vide = désactivé
    )


class StorageSettings(BaseModel):
    backend: str = "memory"
    sqlite_path: str = "./todos.db"
    database_url: str = ""


class YamlConfigSource(PydanticBaseSettingsSource):
    """Loads configuration from a YAML file.

    Priority: init_settings > env_vars > this source > secrets.
    Environment variable naming: APP_APP__PORT=9000 overrides app.port.
    """

    def __init__(self, settings_cls: type[BaseSettings]) -> None:
        super().__init__(settings_cls)
        yaml_path = YAML_CONFIG_PATH
        self._data: dict[str, Any] = {}
        if yaml_path.exists():
            with yaml_path.open() as f:
                self._data = yaml.safe_load(f) or {}

    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> tuple[Any, str, bool]:
        value = self._data.get(field_name)
        return value, field_name, self.field_is_complex(field)

    def __call__(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for field_name, field_info in self.settings_cls.model_fields.items():
            value, key, is_complex = self.get_field_value(field_info, field_name)
            if value is not None:
                result[key] = value
        return result


YAML_CONFIG_PATH = Path("config.yaml")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_nested_delimiter="__",
    )

    app: AppSettings = AppSettings()
    storage: StorageSettings = StorageSettings()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            YamlConfigSource(settings_cls),
            file_secret_settings,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
