# MaiCore-MaiBot 配置系统分析报告

## 1. 配置加载与更新流程

项目的配置系统设计得非常周到，既保证了灵活性，又考虑了版本迭代时的用户体验。其核心围绕 `src/config/config.py` 展开。

**核心流程如下:**

1.  **启动检查**：程序启动时，会首先在 `config/` 目录下查找 `bot_config.toml` 文件。
2.  **首次运行**：如果 `bot_config.toml` 不存在，系统会认为这是第一次运行。它会自动从 `template/bot_config_template.toml` 复制一份模板文件到 `config/` 目录下，并命名为 `bot_config.toml`。然后程序会提示用户填写必要信息并退出，防止在不完整的配置下运行。
3.  **版本更新**：如果 `bot_config.toml` 已存在，系统会读取该文件和模板文件中的 `[inner].version` 字段。
    *   如果版本号相同，则直接加载现有配置，不进行任何修改。
    *   如果版本号不同，说明程序代码有更新，可能引入了新的配置项或修改了旧的。此时，系统会自动执行以下操作：
        a.  将用户当前的 `bot_config.toml` 备份到 `config/old/` 目录下，并附上时间戳，确保用户设置不会丢失。
        b.  复制一份最新的 `bot_config_template.toml` 作为新的 `bot_config.toml`。
        c.  **智能合并**：系统会遍历备份的旧配置文件，将其中的值智能地填充到新的配置文件中。这样既保留了用户的个性化设置，又添加了新版本所需的新配置项。
4.  **数据解析**：配置最终被 `tomlkit` 库加载，并被递归地解析到在 `src/config/config.py` 中定义的 `Config` 数据类（Dataclass）中。这种方式为代码提供了类型安全和清晰的结构。

这个流程确保了用户即使在项目频繁更新后，也无需手动比对和修改配置文件，大大简化了维护工作。

## 2. 配置文件结构 (`.toml`) 详解

配置文件 `bot_config_template.toml` 结构清晰，通过不同的区块（Table）管理着机器人的方方面面。

| 区块 | 主要用途 | 关键配置项说明 |
| :--- | :--- | :--- |
| `[bot]` | **机器人基础信息** | `qq_account`: 机器人登录的QQ号。<br>`nickname`, `alias_names`: 机器人的名字和别名。 |
| `[personality]` | **核心人格** | `personality_core`: 定义机器人核心人设的简短描述，是生成一切回复的基础。 |
| `[identity]` | **身份细节** | `identity_detail`: 描述人格的具体特征，如年龄、外貌、性别等，让人设更丰满。 |
| `[expression]` | **表达风格** | `expression_style`: 控制说话的语气和风格。<br>`enable_expression_learning`: 允许机器人在特定群组中学习人类的说话方式。 |
| `[relationship]` | **关系系统** | `enable_relationship`: 控制是否启用关系演进系统。<br>`relation_frequency`: 决定了从 `NormalChat` 升级到 `FocusChat` 的速度。 |
| `[chat]` | **通用聊天设置** | `chat_mode`: 核心聊天模式切换，可选 `normal`（轻量）, `focus`（重量）, `auto`（自动切换）。<br>`auto_focus_threshold`: 在 `auto` 模式下，控制进入专注模式的敏感度。 |
| `[message_receive]` | **消息过滤** | `ban_words`, `ban_msgs_regex`: 可以通过关键词或正则表达式过滤掉不希望机器人处理的消息。 |
| `[normal_chat]` | **普通聊天模式** | `willing_mode`: 回复意愿模式，决定了机器人回复消息的积极性。<br>`talk_frequency`: 控制回复频率。<br>`mentioned_bot_inevitable_reply`: 被@或提及时是否必须回复。 |
| `[focus_chat]` | **专注聊天模式** | `think_interval`: “思考”的间隔，即 O-P-P-A 循环的执行频率，是性能和消耗的关键。<br>`observation_context_size`: 决定了在专注模式下一次能“看”到多少条上下文消息。 |
| `[focus_chat_processor]`| **专注模式处理器**| 控制专注模式下各个信息处理器的开关，例如是否启用关系识别、工具使用等，用于在功能和消耗之间做取舍。 |
| `[emoji]` | **表情包系统** | `steal_emoji`: 是否自动收集用户发送的表情包。 |
| `[memory]` | **记忆系统** | `enable_memory`: 记忆系统的总开关。<br>`memory_build_interval`, `memory_forget_interval`: 控制记忆形成和遗忘的频率。 |
| `[mood]` | **情绪系统** | 控制情绪值的衰减率和强度，影响机器人在普通聊天中的反应。 |
| `[lpmm_knowledge]` | **本地知识库** | 控制基于知识图谱的RAG（检索增强生成）系统的参数，如搜索的TopK、相似度阈值等。 |
| `[keyword_reaction]` | **关键词触发** | `keyword_rules`, `regex_rules`: 可以设置特定的关键词或正则表达式，一旦匹配到，就触发固定的回复或动作。 |
| `[response_post_process]` | **回复后处理** | 包括是否启用 `chinese_typo`（中文错别字生成器）和 `response_splitter`（长回复分割器），为回复增加“人味”。 |
| `[model]` | **大语言模型配置** | **至关重要**。这里为项目中不同任务（如回复、规划、总结、图像识别等）分别指定了使用的大语言模型（LLM）。每个模型都可以配置 `name`, `provider` (如 SILICONFLOW), `temp` (温度)等参数。 |
| `[maim_message]` | **消息通道** | 用于配置机器人与聊天平台（如QQ）的连接方式。 |
| `[telemetry]` | **遥测** | 是否向开发者发送匿名的统计信息。 |
| `[experimental]` | **实验性功能** | 一些尚未稳定或正在测试的功能的开关。 |

## 3. 如何配置你的机器人

配置机器人非常简单，只需三步：

1.  **复制模板**：进入项目根目录下的 `template/` 文件夹，复制 `bot_config_template.toml` 文件。
2.  **粘贴并重命名**：将复制的文件粘贴到根目录下的 `config/` 文件夹中，并将文件名修改为 `bot_config.toml`。
3.  **修改配置**：打开 `config/bot_config.toml` 文件，至少需要填写以下几项：
    *   `[bot]` -> `qq_account`: 填入你用来登录的机器人QQ号。
    *   `[model]` 下的所有模型配置：根据你使用的大模型服务商（如 [Siliconflow](https://www.siliconflow.cn/)）提供的模型名称和API密钥（如果需要）进行填写。这是机器人能够思考和回复的关键。

完成以上配置后，就可以尝试运行 `bot.py` 来启动你的专属MaiBot了！