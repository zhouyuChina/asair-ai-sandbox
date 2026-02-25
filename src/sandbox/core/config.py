"""全局配置加载

加载 .env → sandbox.yaml → 环境变量插值 → Pydantic 校验 → SandboxConfig。
"""

import os
from pathlib import Path

from sandbox.core.exceptions import ConfigError
from sandbox.schema.config import SandboxConfig
from sandbox.utils.template import interpolate_dict
from sandbox.utils.yaml_loader import load_yaml


def load_dotenv(env_path: str | Path | None = None) -> None:
    """加载 .env 文件中的环境变量（不覆盖已有值）"""
    if env_path is None:
        env_path = Path.cwd() / ".env"
    path = Path(env_path)
    if not path.exists():
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            # 不覆盖已存在的环境变量
            if key not in os.environ:
                os.environ[key] = value


def load_config(config_path: str | Path) -> SandboxConfig:
    """加载并校验 sandbox.yaml 全局配置"""
    path = Path(config_path)
    if not path.exists():
        raise ConfigError(f"配置文件不存在: {path}")

    # 自动加载项目根目录下的 .env 文件
    load_dotenv(path.parent / ".env")

    raw = load_yaml(path)

    # 环境变量插值（仅对 targets / judge / simulated_user 中的敏感字段）
    try:
        interpolated = interpolate_dict(raw)
    except ValueError as e:
        raise ConfigError(f"环境变量插值失败: {e}") from e

    try:
        return SandboxConfig.model_validate(interpolated)
    except Exception as e:
        raise ConfigError(f"配置校验失败: {e}") from e
