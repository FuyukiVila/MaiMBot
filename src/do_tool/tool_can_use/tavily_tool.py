import os
from tavily import AsyncTavilyClient
from src.common.logger import get_module_logger
from src.do_tool.tool_can_use.base_tool import BaseTool, register_tool

logger = get_module_logger("tavily_tool")


class TavilyTool(BaseTool):
    proxies = {
        "http": "http://127.0.0.1:7890",
        "https": "http://127.0.0.1:7890",
    }
    _client = AsyncTavilyClient(
        api_key=os.getenv("TAVILY_API_KEY"),
        proxies=proxies,
    )

    name = "tavily_tool"
    description = """从网络中搜索相关信息"""

    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索查询关键词，可以是一个问题或一个主题",
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
            response = response.encode("utf-8").decode("unicode_escape").replace("\u200b", "")
            # 结果添加到data/raw_info/{query}.txt
            file_path = "data/raw_info"
            file_name = function_args["query"].replace(" ", "-") + ".txt"
            if not os.path.exists(file_path):
                os.makedirs(file_path)
            file_path = os.path.join(file_path, file_name)
            # 如果文件已经存在，则在文件末尾添加内容
            try:
                if os.path.exists(file_path):
                    with open(file_path, "a", encoding="utf-8") as file:
                        file.write(response)
                else:
                    with open(file_path, "w", encoding="utf-8") as file:
                        file.write(response)
            except Exception as e:
                logger.error(f"文件写入失败: {e}")
                pass
            return {"name": self.name, "content": response}
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return {"name": self.name, "content": "搜索失败, 没有结果返回"}


# 注册工具
# register_tool(TavilyTool)
