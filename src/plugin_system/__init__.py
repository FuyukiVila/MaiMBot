"""
MaiBot 插件系统

提供统一的插件开发和管理框架
"""

# 导出主要的公共接口
from .base import (
    BasePlugin,
    BaseAction,
    BaseCommand,
    ConfigField,
    ComponentType,
    ActionActivationType,
    ChatMode,
    ComponentInfo,
    ActionInfo,
    CommandInfo,
    PluginInfo,
    PythonDependency,
    BaseEventHandler,
    EventHandlerInfo,
    EventType,
    MaiMessages,
)
from .core import (
    plugin_manager,
    component_registry,
    dependency_manager,
    events_manager,
)

# 导入工具模块
from .utils import (
    ManifestValidator,
    # ManifestGenerator,
    # validate_plugin_manifest,
    # generate_plugin_manifest,
)

from .apis import register_plugin, get_logger


__version__ = "1.0.0"

__all__ = [
    # 基础类
    "BasePlugin",
    "BaseAction",
    "BaseCommand",
    "BaseEventHandler",
    # 类型定义
    "ComponentType",
    "ActionActivationType",
    "ChatMode",
    "ComponentInfo",
    "ActionInfo",
    "CommandInfo",
    "PluginInfo",
    "PythonDependency",
    "EventHandlerInfo",
    "EventType",
    # 消息
    "MaiMessages",
    # 管理器
    "plugin_manager",
    "component_registry",
    "dependency_manager",
    "events_manager",
    # 装饰器
    "register_plugin",
    "ConfigField",
    # 工具函数
    "ManifestValidator",
    "get_logger",
    # "ManifestGenerator",
    # "validate_plugin_manifest",
    # "generate_plugin_manifest",
]
