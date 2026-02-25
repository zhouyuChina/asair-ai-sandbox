"""全局配置加载

加载 sandbox.yaml → 环境变量插值 → Pydantic 校验 → SandboxConfig。
"""

from pathlib import Path

from sandbox.core.exceptions import ConfigError
from sandbox.schema.config import SandboxConfig
from sandbox.utils.template import interpolate_dict
from sandbox.utils.yaml_loader import load_yaml


def load_config(config_path: str | Path) -> SandboxConfig:
    """加载并校验 sandbox.yaml 全局配置"""
    path = Path(config_path)
    if not path.exists():
        raise ConfigError(f"配置文件不存在: {path}")

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
