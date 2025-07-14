# 项目进度

## 2025-06-12

*   **修复:** 解决了在 [`src/chat/focus_chat/heartFC_chat.py`](src/chat/focus_chat/heartFC_chat.py) 中因导入了不存在的模块 `mind_processor` 导致的 `ModuleNotFoundError`。通过委派给 Code 模式，将导入语句修正为 `from src.chat.focus_chat.info_processors.notused_mind_processor import MindProcessor`，成功解决了该问题。

## 2025-06-11

*   **修复:** 解决了在 `src/llm_models/utils_model.py` 中因调用了日志库 `structlog` 不支持的 `trace` 方法而导致的 `AttributeError`。通过委派给 Code 模式，将所有 `logger.trace()` 调用替换为 `logger.debug()`，成功解决了该问题。
*   **修复:** 解决了在 `src/main.py` 中因错误地在函数 `get_emoji_manager` 而非其返回的实例上调用 `initialize` 方法，导致的 `AttributeError`。通过委派给 Code 模式，将调用方式修正为 `get_emoji_manager().initialize()`，成功解决了该启动错误。
*   **修复:** 解决了在启动时因 `TavilyTool` 在 `src/tools/tool_can_use/tavily_tool.py` 中过早实例化 `AsyncTavilyClient` 且未提供 `TAVILY_API_KEY` 导致的 `MissingAPIKeyError`。通过委派给 Code 模式，实现了客户端的懒加载，确保了程序的健壮性。
*   **修复:** 解决了在启动时因 [`src/tools/tool_can_use/eval_tool.py`](src/tools/tool_can_use/eval_tool.py) 中使用了错误的函数名 `get_module_logger` 导致的 `ImportError`。通过委派给 Code 模式，将函数名修正为 `get_logger`，成功解决了该问题。

## 2025-06-09

*   **修复:** 解决了在 `scripts/info_extraction.py` 脚本执行过程中，因 [`src/chat/knowledge/raw_processing.py`](src/chat/knowledge/raw_processing.py:6) 中错误的导入语句 `from src.chat.knowledge.utils import get_sha256` 导致的 `ImportError`。通过委派给 Code 模式，将导入语句修正为 `from src.chat.knowledge.utils.hash import get_sha256`，成功解决了该问题。

## 2025-06-03

*   **修复:** 解决了在 [`src/chat/focus_chat/expressors/exprssion_learner.py`](src/chat/focus_chat/expressors/exprssion_learner.py:134) 中因 `learn_expression` 返回 `None` 导致的 `TypeError: cannot unpack non-iterable NoneType object` 错误。Debug 模式通过在解包前添加 `None` 检查来修复此问题。
*   **优化:** Code 模式优化了 [`config/bot_config_dev.toml`](config/bot_config_dev.toml) 中的 prompt 内容，包括重写核心设定中的互动指南 (`<interaction_guide>`)，简化 `personality_sides`，并更新 `expression_style`，使其更清晰、简洁和一致。