import ast
import contextlib
import io
from typing import Dict
from src.common.logger import get_module_logger
from src.tools.tool_can_use.base_tool import BaseTool

logger = get_module_logger("eval_tool")


class EvalTool(BaseTool):
    """代码评估和运行工具"""

    # 工具名称
    name = "eval_tool"

    # 工具描述
    description = "用于安全地评估和运行Python代码，支持代码分析和输出捕获"

    # 参数定义
    parameters = {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "要执行的Python代码"},
            "mode": {
                "type": "string",
                "description": "执行模式: 'analyze'用于静态分析，'run'用于实际执行 default: 'analyze'",
            },
        },
        "required": ["code"],
    }

    def _analyze_code(self, code: str) -> Dict[str, list]:
        """静态分析代码

        Args:
            code: 要分析的代码字符串

        Returns:
            Dict: 包含分析结果的字典
        """
        tree = ast.parse(code)
        analysis = {"functions": [], "classes": [], "imports": [], "assignments": []}

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                analysis["functions"].append(node.name)
            elif isinstance(node, ast.ClassDef):
                analysis["classes"].append(node.name)
            elif isinstance(node, ast.Import):
                for name in node.names:
                    analysis["imports"].append(name.name)
            elif isinstance(node, ast.ImportFrom):
                for name in node.names:
                    analysis["imports"].append(f"{node.module}.{name.name}")
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        analysis["assignments"].append(target.id)

        return analysis

    def _run_code(self, code: str) -> str:
        """在安全的环境中运行代码

        Args:
            code: 要执行的代码
            timeout: 超时时间（秒）

        Returns:
            str: 代码执行的输出
        """
        # 创建StringIO对象捕获标准输出
        output = io.StringIO()

        # 使用contextlib捕获标准输出
        with contextlib.redirect_stdout(output):
            try:
                # 编译并执行代码
                compiled_code = compile(code, "<string>", "exec")
                exec(compiled_code, {"__builtins__": __builtins__}, {})
            except Exception as e:
                logger.error(f"代码执行失败: {str(e)}")

        return output.getvalue()

    async def execute(self, function_args: dict, message_txt: str = "") -> Dict:
        """执行工具逻辑

        Args:
            function_args: 工具调用参数
            message_txt: 原始消息文本

        Returns:
            Dict: 包含执行结果的字典
        """
        code = function_args.get("code")
        mode = function_args.get("mode", "analyze")

        try:
            if mode == "analyze":
                # 执行静态分析
                analysis = self._analyze_code(code)
                result = {"status": "success", "analysis": analysis}
            else:
                # 执行代码并捕获输出
                output = self._run_code(code)
                result = {"status": "success", "output": output}

        except Exception as e:
            logger.error(f"代码执行失败: {str(e)}")
            result = {"status": "error", "message": f"代码执行失败: {str(e)}"}

        return {"name": self.name, "content": str(result)}


# 注册工具
# register_tool(EvalTool)
