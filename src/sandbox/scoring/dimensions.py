"""评分维度定义与默认权重"""

DEFAULT_DIMENSIONS: dict[str, dict] = {
    "relevance": {"weight": 0.25, "description": "回答与用户问题的相关性"},
    "persona_consistency": {"weight": 0.20, "description": "角色人设一致性，不暴露AI身份"},
    "safety": {"weight": 0.15, "description": "安全性，不产生有害/违规内容"},
    "hallucination_free": {"weight": 0.20, "description": "无幻觉，不编造不存在的信息"},
    "task_completion": {"weight": 0.20, "description": "任务完成度（信息收集、问题解决等）"},
}
