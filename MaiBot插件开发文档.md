# MaiBot 插件开发文档

## 📖 总体介绍

MaiBot 是一个基于大语言模型的智能聊天机器人，采用现代化的插件系统架构，支持灵活的功能扩展和定制。插件系统提供了统一的开发框架，让开发者可以轻松创建和管理各种功能组件。

### 🎯 插件系统特点

- **组件化架构**：支持Action（动作）和Command（命令）两种主要组件类型
- **统一API接口**：提供丰富的API功能，包括消息发送、数据库操作、LLM调用等
- **配置驱动**：支持TOML配置文件，实现灵活的参数配置
- **热加载机制**：支持动态加载和卸载插件
- **依赖管理**：内置依赖检查和解析机制
- **拦截控制**：Command组件支持消息拦截控制

## 🧩 主要组件

### 1. 插件（Plugin）

插件是功能的容器，每个插件可以包含多个组件。插件通过继承 `BasePlugin` 类实现：

```python
from src.plugin_system import BasePlugin, register_plugin

@register_plugin
class MyPlugin(BasePlugin):
    plugin_name = "my_plugin"
    plugin_description = "我的插件"
    plugin_version = "1.0.0"
    plugin_author = "开发者"
    config_file_name = "config.toml"  # 可选配置文件
```

### 2. Action组件

Action是给麦麦在回复之外提供额外功能的组件，由麦麦的决策系统自主选择是否使用，具有随机性和拟人化的调用特点。Action不是直接响应用户命令，而是让麦麦根据聊天情境智能地选择合适的动作，使其行为更加自然和真实。

```python
from src.plugin_system import BaseAction, ActionActivationType, ChatMode

class MyAction(BaseAction):
    # 激活设置 - 麦麦会根据这些条件决定是否使用此Action
    focus_activation_type = ActionActivationType.KEYWORD
    normal_activation_type = ActionActivationType.RANDOM
    activation_keywords = ["关键词1", "关键词2"]
    mode_enable = ChatMode.ALL
    
    async def execute(self) -> Tuple[bool, str]:
        # 麦麦决定使用此Action时执行的逻辑
        await self.send_text("这是麦麦主动执行的动作")
        return True, "执行成功"
```

### 3. Command组件

Command是直接响应用户明确指令的组件，与Action不同，Command是被动触发的，当用户输入特定格式的命令时立即执行。Command支持正则表达式匹配和消息拦截：

```python
from src.plugin_system import BaseCommand

class MyCommand(BaseCommand):
    command_pattern = r"^/hello\s+(?P<name>\w+)$"
    command_help = "打招呼命令"
    command_examples = ["/hello 世界"]
    intercept_message = True  # 拦截后续处理
    
    async def execute(self) -> Tuple[bool, Optional[str]]:
        name = self.matched_groups.get("name", "世界")
        await self.send_text(f"你好，{name}！")
        return True, f"已向{name}问候"
```

> **Action vs Command 区别**：
> - **Action**：麦麦主动决策使用，具有随机性和智能性，让麦麦行为更拟人化
> - **Command**：用户主动触发，确定性执行，用于提供具体功能和服务

## 🚀 快速开始

### 1. 创建插件目录

在项目的 `src/plugins/` 文件夹下创建你的插件目录：

```
src/plugins/
└── my_plugin/
    ├── plugin.py      # 插件主文件
    ├── config.toml    # 配置文件（可选）
    └── README.md      # 说明文档（可选）
```

### 2. 编写插件主文件

创建 `plugin.py` 文件：

```python
from typing import List, Tuple, Type
from src.plugin_system import (
    BasePlugin, register_plugin, BaseAction, BaseCommand,
    ComponentInfo, ActionActivationType, ChatMode
)

# 定义一个简单的Action
class GreetingAction(BaseAction):
    focus_activation_type = ActionActivationType.KEYWORD
    activation_keywords = ["你好", "hello"]
    
    async def execute(self) -> Tuple[bool, str]:
        await self.send_text("你好！很高兴见到你！")
        return True, "执行问候动作"

# 定义一个简单的Command
class InfoCommand(BaseCommand):
    command_pattern = r"^/info$"
    command_help = "显示插件信息"
    command_examples = ["/info"]
    
    async def execute(self) -> Tuple[bool, str]:
        await self.send_text("这是我的第一个插件！")
        return True, "显示插件信息"

# 注册插件
@register_plugin
class MyFirstPlugin(BasePlugin):
    plugin_name = "first_plugin"
    plugin_description = "我的第一个插件"
    plugin_version = "1.0.0"
    plugin_author = "我的名字"
    
    def get_plugin_components(self) -> List[Tuple[ComponentInfo, Type]]:
        return [
            (GreetingAction.get_action_info(
                name="greeting", 
                description="问候用户"
            ), GreetingAction),
            (InfoCommand.get_command_info(
                name="info", 
                description="显示插件信息"
            ), InfoCommand),
        ]
```

### 3. 创建配置文件（可选）

创建 `config.toml` 文件：

```toml
[plugin]
name = "first_plugin"
version = "1.0.0"
enabled = true

[greeting]
enable_emoji = true
custom_message = "欢迎使用我的插件！"

[logging]
level = "INFO"
```

### 4. 启动机器人

将插件放入 `src/plugins/` 目录后，启动MaiBot，插件会自动加载。

## 📚 完整说明

### 插件生命周期

1. **发现阶段**：系统扫描 `src/plugins/` 目录，查找Python文件
2. **加载阶段**：导入插件模块，注册插件类
3. **实例化阶段**：创建插件实例，加载配置文件
4. **注册阶段**：注册插件及其包含的组件
5. **运行阶段**：组件根据条件被激活和执行

### Action组件详解

Action组件是麦麦智能决策系统的重要组成部分，它们不是被动响应用户输入，而是由麦麦根据聊天情境主动选择执行。这种设计使麦麦的行为更加拟人化和自然，就像真人聊天时会根据情况做出不同的反应一样。

#### 激活类型

Action的激活类型决定了麦麦在什么情况下会考虑使用该Action：

- `NEVER`：从不激活，通常用于临时禁用
- `ALWAYS`：麦麦总是会考虑使用此Action
- `LLM_JUDGE`：通过LLM智能判断当前情境是否适合使用
- `RANDOM`：基于随机概率决定是否使用，增加行为的不可预测性
- `KEYWORD`：当检测到特定关键词时会考虑使用

#### 聊天模式

- `FOCUS`：专注聊天模式
- `NORMAL`：普通聊天模式
- `ALL`：所有模式

#### Action示例

```python
class AdvancedAction(BaseAction):
    # 激活设置
    focus_activation_type = ActionActivationType.LLM_JUDGE
    normal_activation_type = ActionActivationType.KEYWORD
    activation_keywords = ["帮助", "help"]
    llm_judge_prompt = "当用户需要帮助时回答'是'，否则回答'否'"
    random_activation_probability = 0.3
    mode_enable = ChatMode.ALL
    parallel_action = True
    
    # 动作参数（用于LLM规划）
    action_parameters = {
        "query": "用户的问题或需求"
    }
    
    # 使用场景描述
    action_require = [
        "用户明确请求帮助",
        "检测到用户遇到困难"
    ]
    
    async def execute(self) -> Tuple[bool, str]:
        query = self.action_data.get("query", "")
        
        # 麦麦主动决定帮助用户时执行的逻辑
        await self.send_text(f"我来帮助你解决：{query}")
        await self.send_type("emoji", "😊")
        
        # 存储执行记录
        await self.api.store_action_info(
            action_build_into_prompt=True,
            action_prompt_display=f"麦麦主动帮助用户：{query}",
            action_done=True,
            thinking_id=self.thinking_id
        )
        
        return True, f"麦麦已主动帮助处理：{query}"
```

### Command组件详解

#### 正则表达式匹配

Command使用正则表达式匹配用户输入，支持命名组捕获：

```python
class UserCommand(BaseCommand):
    # 匹配 /user add 用户名
    command_pattern = r"^/user\s+(?P<action>add|del|info)\s+(?P<username>\w+)$"
    command_help = "用户管理命令"
    command_examples = [
        "/user add 张三",
        "/user del 李四", 
        "/user info 王五"
    ]
    intercept_message = True
    
    async def execute(self) -> Tuple[bool, str]:
        action = self.matched_groups.get("action")
        username = self.matched_groups.get("username")
        
        if action == "add":
            return await self._add_user(username)
        elif action == "del":
            return await self._delete_user(username)
        elif action == "info":
            return await self._show_user_info(username)
        
        return False, "无效的操作"
```

#### 消息拦截控制

- `intercept_message = True`：拦截消息，不进行后续处理
- `intercept_message = False`：不拦截，继续处理其他组件

### 配置系统

插件支持TOML配置文件，配置会自动加载到插件实例：

```python
class ConfigurablePlugin(BasePlugin):
    config_file_name = "config.toml"
    
    def some_method(self):
        # 获取配置值，支持嵌套键访问
        max_items = self.get_config("limits.max_items", 10)
        custom_message = self.get_config("messages.greeting", "默认消息")
```

配置文件格式：

```toml
[limits]
max_items = 20
timeout = 30

[messages]
greeting = "欢迎使用配置化插件！"
error = "操作失败"

[features]
enable_debug = true
```

### 错误处理

插件应该包含适当的错误处理：

```python
async def execute(self) -> Tuple[bool, str]:
    try:
        # 执行逻辑
        result = await self._do_something()
        return True, "操作成功"
    except ValueError as e:
        logger.error(f"{self.log_prefix} 参数错误: {e}")
        await self.send_text("参数错误，请检查输入")
        return False, f"参数错误: {e}"
    except Exception as e:
        logger.error(f"{self.log_prefix} 执行失败: {e}")
        await self.send_text("操作失败，请稍后重试")
        return False, f"执行失败: {e}"
```

## 🔌 API说明

### 消息API

插件可以通过 `self.api` 访问各种API功能：

#### 基础消息发送

```python
# 发送文本消息
await self.send_text("这是文本消息")

# 发送特定类型消息
await self.send_type("emoji", "😊")
await self.send_type("image", image_url)

# 发送命令消息
await self.send_command("命令名", {"参数": "值"})
```

#### 高级消息发送

```python
# 向指定群聊发送消息
await self.api.send_text_to_group("消息内容", "群ID", "qq")

# 向指定用户发送私聊消息
await self.api.send_text_to_user("消息内容", "用户ID", "qq")

# 向指定目标发送任意类型消息
await self.api.send_message_to_target(
    message_type="text",
    content="消息内容",
    platform="qq",
    target_id="目标ID",
    is_group=True,
    display_message="显示消息"
)
```

#### 消息查询

```python
# 获取聊天类型
chat_type = self.api.get_chat_type()  # "group" 或 "private"

# 获取最近消息
recent_messages = self.api.get_recent_messages(count=5)
```

### 数据库API

插件可以使用数据库API进行数据持久化：

#### 通用查询

```python
# 查询数据
results = await self.api.db_query(
    model_class=SomeModel,
    query_type="get",
    filters={"field": "value"},
    limit=10,
    order_by=["-time"]
)

# 创建记录
new_record = await self.api.db_query(
    model_class=SomeModel,
    query_type="create",
    data={"field1": "value1", "field2": "value2"}
)

# 更新记录
updated_count = await self.api.db_query(
    model_class=SomeModel,
    query_type="update",
    filters={"id": 123},
    data={"field": "new_value"}
)

# 删除记录
deleted_count = await self.api.db_query(
    model_class=SomeModel,
    query_type="delete",
    filters={"id": 123}
)

# 计数
count = await self.api.db_query(
    model_class=SomeModel,
    query_type="count",
    filters={"active": True}
)
```

#### 原始SQL查询

```python
# 执行原始SQL
results = await self.api.db_raw_query(
    sql="SELECT * FROM table WHERE condition = ?",
    params=["value"],
    fetch_results=True
)
```

#### Action记录存储

```python
# 存储Action执行记录
await self.api.store_action_info(
    action_build_into_prompt=True,
    action_prompt_display="显示的动作描述",
    action_done=True,
    thinking_id="思考ID",
    action_data={"key": "value"}
)
```

### LLM API

插件可以调用大语言模型：

```python
# 获取可用模型
models = self.api.get_available_models()

# 使用模型生成内容
success, response, reasoning, model_name = await self.api.generate_with_model(
    prompt="你的提示词",
    model_config=models["某个模型"],
    request_type="plugin.generate",
    temperature=0.7,
    max_tokens=1000
)

if success:
    await self.send_text(f"AI回复：{response}")
else:
    await self.send_text("AI生成失败")
```

### 配置API

```python
# 获取全局配置
global_config = self.api.get_global_config()

# 获取插件配置
plugin_config = self.api.get_config("section.key", "默认值")
```

### 工具API

```python
# 获取当前时间戳
timestamp = self.api.get_current_timestamp()

# 格式化时间
formatted_time = self.api.format_timestamp(timestamp, "%Y-%m-%d %H:%M:%S")

# JSON处理
json_str = self.api.dict_to_json({"key": "value"})
data = self.api.json_to_dict(json_str)

# 生成UUID
uuid = self.api.generate_uuid()

# 哈希计算
hash_value = self.api.calculate_hash("text", "md5")
```

### 流API

```python
# 获取当前聊天流信息
chat_stream = self.api.get_service("chat_stream")
if chat_stream:
    stream_id = chat_stream.stream_id
    platform = chat_stream.platform
    
    # 群聊信息
    if chat_stream.group_info:
        group_id = chat_stream.group_info.group_id
        group_name = chat_stream.group_info.group_name
    
    # 用户信息
    user_id = chat_stream.user_info.user_id
    user_name = chat_stream.user_info.user_nickname
```

### 心流API

```python
# 等待新消息
has_new_message = await self.api.wait_for_new_message(timeout=30)

# 获取观察信息
observations = self.api.get_service("observations")
```

## 🔧 高级功能

### 插件依赖管理

```python
@register_plugin
class DependentPlugin(BasePlugin):
    plugin_name = "dependent_plugin"
    plugin_description = "依赖其他插件的插件"
    dependencies = ["core_actions", "example_plugin"]  # 依赖列表
    
    def get_plugin_components(self):
        # 只有依赖满足时才会加载
        return [...]
```

### 并行Action

```python
class ParallelAction(BaseAction):
    parallel_action = True  # 允许与其他Action并行执行
    
    async def execute(self) -> Tuple[bool, str]:
        # 这个Action可以与其他并行Action同时执行
        return True, "并行执行完成"
```

### 动态配置更新

```python
class DynamicPlugin(BasePlugin):
    def get_plugin_components(self):
        # 根据配置动态决定加载哪些组件
        components = []
        
        if self.get_config("features.enable_greeting", True):
            components.append((GreetingAction.get_action_info(), GreetingAction))
        
        if self.get_config("features.enable_commands", True):
            components.append((SomeCommand.get_command_info(), SomeCommand))
        
        return components
```

### 自定义元数据

```python
class MetadataAction(BaseAction):
    @classmethod
    def get_action_info(cls, name=None, description=None):
        info = super().get_action_info(name, description)
        # 添加自定义元数据
        info.metadata = {
            "category": "utility",
            "priority": "high",
            "custom_field": "custom_value"
        }
        return info
```

## 📋 开发规范

### 1. 命名规范

- 插件名使用小写字母和下划线：`my_plugin`
- 类名使用大驼峰：`MyPlugin`、`GreetingAction`
- 方法名使用小写字母和下划线：`execute`、`send_message`

### 2. 文档规范

- 所有插件类都应该有完整的文档字符串
- Action和Command的描述要清晰明确
- 提供使用示例和配置说明

### 3. 错误处理

- 所有异步操作都要包含异常处理
- 使用日志记录错误信息
- 向用户返回友好的错误消息

### 4. 配置管理

- 敏感配置不要硬编码在代码中
- 提供合理的默认值
- 支持配置热更新

### 5. 性能考虑

- 避免在初始化时执行耗时操作
- 合理使用缓存减少重复计算
- 及时释放不需要的资源

## 🎯 最佳实践

### 1. 插件结构

```
src/plugins/my_plugin/
├── __init__.py       # 空文件或简单导入
├── plugin.py         # 主插件文件
├── actions/          # Action组件目录
│   ├── __init__.py
│   ├── greeting.py
│   └── helper.py
├── commands/         # Command组件目录
│   ├── __init__.py
│   ├── admin.py
│   └── user.py
├── utils/            # 工具函数
│   ├── __init__.py
│   └── helpers.py
├── config.toml       # 配置文件
└── README.md         # 说明文档
```

### 2. 模块化设计

```python
# actions/greeting.py
from src.plugin_system import BaseAction

class GreetingAction(BaseAction):
    # ... 实现细节

# commands/admin.py  
from src.plugin_system import BaseCommand

class AdminCommand(BaseCommand):
    # ... 实现细节

# plugin.py
from .actions.greeting import GreetingAction
from .commands.admin import AdminCommand

@register_plugin
class MyPlugin(BasePlugin):
    def get_plugin_components(self):
        return [
            (GreetingAction.get_action_info(), GreetingAction),
            (AdminCommand.get_command_info(), AdminCommand),
        ]
```

### 3. 配置分层

```toml
# config.toml
[plugin]
name = "my_plugin"
version = "1.0.0"
enabled = true

[components]
enable_greeting = true
enable_admin = false

[greeting]
message_template = "你好，{username}！"
enable_emoji = true

[admin]
allowed_users = ["admin", "moderator"]
```

### 4. 日志实践

```python
from src.common.logger import get_logger

logger = get_logger("my_plugin")

class MyAction(BaseAction):
    async def execute(self):
        logger.info(f"{self.log_prefix} 开始执行动作")
        
        try:
            # 执行逻辑
            result = await self._do_something()
            logger.debug(f"{self.log_prefix} 执行结果: {result}")
            return True, "成功"
        except Exception as e:
            logger.error(f"{self.log_prefix} 执行失败: {e}", exc_info=True)
            return False, str(e)
```

---

## 🎉 总结

MaiBot的插件系统提供了强大而灵活的扩展能力，通过Action和Command两种组件类型，开发者可以轻松实现各种功能。系统提供了丰富的API接口、完善的配置管理和错误处理机制，让插件开发变得简单高效。

遵循本文档的指导和最佳实践，你可以快速上手MaiBot插件开发，为机器人添加强大的自定义功能。

如有问题或建议，欢迎提交Issue或参与讨论！ 