"""旧版 config.json 字段定义（v0.32.0 向后兼容）

此模块定义需要提示用户迁移的旧版 nanobot 字段列表，
供 ConfigManager.check_legacy_fields()、migrate_config()、InitWizard 共享。
"""

# 旧版 config.json 中需提示迁移的 nanobot 字段（规格 7.3 向后兼容）
LEGACY_NANOBOT_FIELDS: list[str] = [
    "llm_provider",
    "llm_model",
    "llm_base_url",
    "fallback_models",
    "model_presets",
]
