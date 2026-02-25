"""环境变量插值工具

支持 ${ENV_VAR} 语法，将配置值中的环境变量引用替换为实际值。
"""

import os
import re

_ENV_PATTERN = re.compile(r"\$\{([^}]+)\}")


def interpolate_env(value: str) -> str:
    """将字符串中的 ${VAR} 替换为环境变量值"""

    def _replace(match: re.Match) -> str:
        var_name = match.group(1)
        env_val = os.environ.get(var_name)
        if env_val is None:
            raise ValueError(f"环境变量未设置: {var_name}")
        return env_val

    return _ENV_PATTERN.sub(_replace, value)


def interpolate_dict(data: dict) -> dict:
    """递归替换字典中所有字符串值的环境变量引用"""
    result = {}
    for key, value in data.items():
        if isinstance(value, str):
            result[key] = interpolate_env(value)
        elif isinstance(value, dict):
            result[key] = interpolate_dict(value)
        elif isinstance(value, list):
            result[key] = [
                interpolate_env(item) if isinstance(item, str) else item for item in value
            ]
        else:
            result[key] = value
    return result
