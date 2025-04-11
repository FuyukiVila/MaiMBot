from src.do_tool.tool_can_use.base_tool import BaseTool, register_tool
from tavily import AsyncTavilyClient
import os


class TavilyTool(BaseTool):
    proxies = {
        "http": "http://127.0.0.1:7890",
        "https": "http://127.0.0.1:7890",
    }
    _client = AsyncTavilyClient(
        api_key=os.getenv("TAVILY_API_KEY"),
        proxies=proxies,
    )

    name = "tavily"
    description = """调用Tavily API进行网络搜索以获取相关上下文信息"""

    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词，可以是一个问题或一个主题",
            },
            "max_results": {
                "type": "number",
                "description": "最大返回结果数量, default: 5, range: 1-10",
            },
        },
        "required": ["query"],
    }

    async def execute(self, function_args, message_txt=""):
        """执行Tavily搜索"""
        try:
            response = await self._client.get_search_context(
                query=function_args["query"],
                max_results=function_args.get("max_results", 5),
            )

            return {"name": self.name, "content": response}
        except Exception as e:
            return {"name": self.name, "content": "搜索失败, 没有结果返回"}


# 注册工具
register_tool(TavilyTool)
