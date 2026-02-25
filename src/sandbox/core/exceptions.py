"""自定义异常定义"""


class SandboxError(Exception):
    """Sandbox 基础异常"""


class ConfigError(SandboxError):
    """配置加载或校验错误"""


class DifyAPIError(SandboxError):
    """Dify API 调用错误"""

    def __init__(self, message: str, status_code: int | None = None, response_body: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class AssertionError_(SandboxError):
    """断言执行错误（非断言失败，而是断言本身出错）"""


class YAMLValidationError(SandboxError):
    """YAML 文件校验失败"""

    def __init__(self, message: str, file_path: str | None = None):
        super().__init__(message)
        self.file_path = file_path
