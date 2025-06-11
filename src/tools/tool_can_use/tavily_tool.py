import os
from tavily import AsyncTavilyClient
from src.common.logger import get_logger
from src.tools.tool_can_use.base_tool import BaseTool

logger = get_logger("tavily_tool")


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
    description = """从网络中搜索相关信息，对于任何你不知道的事情，或者需要最新信息的事情，使用这个工具。"""

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
            response = await self._client.search(
                query=function_args["query"],
                max_results=function_args.get("max_results", 5),
                search_depth="advanced",
                include_answer="advanced",
            )
            answer = response.get("answer", None)
            if not answer:
                return {"name": self.name, "content": "没有找到相关结果"}
            logger.info(f"搜索结果: {answer}")
            # 结果添加到data/lpmm_raw_data/{query}.txt
            file_path = "data/lpmm_raw_data"
            file_name = function_args["query"].replace(" ", "-") + ".txt"
            if not os.path.exists(file_path):
                os.makedirs(file_path)
            file_path = os.path.join(file_path, file_name)
            # 如果文件已经存在，则在文件末尾添加内容
            try:
                if os.path.exists(file_path):
                    with open(file_path, "a", encoding="utf-8") as file:
                        file.write(answer)
                else:
                    with open(file_path, "w", encoding="utf-8") as file:
                        file.write(answer)
            except Exception as e:
                logger.error(f"文件写入失败: {e}")
                pass
            return {"name": self.name, "content": answer}
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return {"name": self.name, "content": "搜索失败, 没有结果返回"}


# 注册工具
# register_tool(TavilyTool)
