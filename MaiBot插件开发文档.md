# MaiBot 插件开发文档

## 📖 总体介绍

MaiBot 是一个基于大语言模型的智能聊天机器人，采用现代化的插件系统架构，支持灵活的功能扩展和定制。插件系统提供了统一的开发框架，让开发者可以轻松创建和管理各种功能组件。

### 🎯 插件系统特点

- **组件化架构**：支持Action（动作）和Command（命令）两种主要组件类型
- **统一API接口**：提供丰富的API功能，包括消息发送、数据库操作、LLM调用等
- **配置驱动**：支持TOML配置文件，实现灵活的参数配置
- **热加载机制**：支持动态加载和卸载插件
- **智能依赖管理**：自动检查和安装Python第三方包依赖
- **拦截控制**：Command组件支持消息拦截控制
- **双目录支持**：区分用户插件和系统内置插件

### 📂 插件目录说明

> ⚠️ **重要**：请将你的自定义插件放在项目根目录的 `plugins/` 文件夹下！

MaiBot支持两个插件目录：

- **`plugins/`** (项目根目录)：**用户自定义插件目录**，这是你应该放置插件的位置
- **`src/plugins/builtin/`**：**系统内置插件目录**，包含核心功能插件，请勿修改

**优先级**：用户插件 > 系统内置插件（同名时用户插件会覆盖系统插件）

## 📚 文档导航

### 🚀 快速入门
- [🚀 快速开始指南](docs/plugins/quick-start.md) - 5分钟创建你的第一个插件
- [📋 开发规范](docs/plugins/development-standards.md) - 代码规范和最佳实践

### 📖 核心概念
- [⚡ Action组件详解](docs/plugins/action-components.md) - 智能动作组件开发指南
- [💻 Command组件详解](docs/plugins/command-components.md) - 命令组件开发指南
- [🔧 工具系统详解](docs/plugins/tool-system.md) - 扩展麦麦信息获取能力的工具组件
- [📦 依赖管理系统](docs/plugins/dependency-management.md) - Python包依赖管理详解

### 🔌 API参考
- [📡 消息API](docs/plugins/api/message-api.md) - 消息发送和处理接口

### 💡 示例和模板
- [📚 完整示例](docs/plugins/examples/complete-examples.md) - 各种类型的插件示例


## 🎉 快速开始

想立即开始开发？跳转到 [🚀 快速开始指南](docs/plugins/quick-start.md)，5分钟内创建你的第一个MaiBot插件！

## 💬 社区和支持

- 📖 **文档问题**：如果发现文档错误或需要改进，请提交Issue
- 🐛 **Bug报告**：在GitHub上报告插件系统相关的问题
- 💡 **功能建议**：欢迎提出新功能建议和改进意见
- 🤝 **贡献代码**：欢迎提交PR改进插件系统

---

**开始你的MaiBot插件开发之旅吧！** 🚀 