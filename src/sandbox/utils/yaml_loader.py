"""安全 YAML 加载 + Pydantic 校验"""

from pathlib import Path
from typing import TypeVar

import yaml
from pydantic import BaseModel, ValidationError

from sandbox.core.exceptions import YAMLValidationError

T = TypeVar("T", bound=BaseModel)


def load_yaml(path: str | Path) -> dict:
    """安全加载 YAML 文件，返回字典"""
    path = Path(path)
    if not path.exists():
        raise YAMLValidationError(f"文件不存在: {path}", file_path=str(path))
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise YAMLValidationError(f"YAML 顶层必须是字典: {path}", file_path=str(path))
    return data


def load_and_validate(path: str | Path, model: type[T]) -> T:
    """加载 YAML 文件并用 Pydantic 模型校验"""
    data = load_yaml(path)
    try:
        return model.model_validate(data)
    except ValidationError as e:
        raise YAMLValidationError(
            f"YAML 校验失败 ({path}):\n{e}", file_path=str(path)
        ) from e
