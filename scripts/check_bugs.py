"""全面代码审查：语法、导入、常见 bug"""
import os
import ast
import sys

root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")

issues = []

for dirpath, _, filenames in os.walk(root):
    for fn in filenames:
        if not fn.endswith(".py"):
            continue
        fpath = os.path.join(dirpath, fn)
        rel = os.path.relpath(fpath, root)

        with open(fpath, "r", encoding="utf-8") as f:
            source = f.read()

        # 1. 语法检查（已做，跳过）
        try:
            compile(source, fpath, "exec")
        except SyntaxError as e:
            issues.append(f"[SYNTAX] {rel}:{e.lineno}: {e.msg}")
            continue

        # 2. AST 分析
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue

        # 3. 检查特定模式
        lines = source.split("\n")

        for i, line in enumerate(lines, 1):
            s = line.strip()

            # 检查 U+2026 非法字符
            if "\u2026" in line:
                issues.append(f"[BADCHAR] {rel}:{i}: 发现非法省略号 ... 字符")

            # 检查 f-string 中直接嵌套字典的 yield/return（Python 3.11 不兼容）
            if s.startswith("yield ") or s.startswith("return "):
                if "f'" in s or 'f"' in s:
                    # 粗略检查是否有深层嵌套 {{}}
                    in_fstring = False
                    depth = 0
                    for ch in s:
                        if ch in ("'", '"'):
                            in_fstring = not in_fstring
                        if in_fstring and ch == "{":
                            depth += 1
                        if in_fstring and ch == "}":
                            depth -= 1
                    if depth > 2:
                        issues.append(f"[FSTRING] {rel}:{i}: f-string 深度嵌套大括号 (depth={depth}), 可能 Python 3.11 不兼容")

            # 检查 settings.xxx 但没有正确导入
            if "settings." in s and "import" not in s and s.startswith("#") == False:
                # 只是粗略检查，忽略 import 语句
                pass

            # 检查 try/except 裸 except
            if s == "except:":
                issues.append(f"[WARN] {rel}:{i}: 裸 except (会捕获 KeyboardInterrupt 等)")

        # 4. 检查模块级别的潜在导入问题
        if "__init__" in fn:
            continue

        # 检查是否有明显的 await 遗漏
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                # 检查 async def 内部是否有同步阻塞调用
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        func_name = ""
                        if isinstance(child.func, ast.Attribute):
                            func_name = child.func.attr
                        elif isinstance(child.func, ast.Name):
                            func_name = child.func.id
                        # 常见需要 await 的调用
                        suspicious = ["execute", "fetchall", "fetchone", "scalar", "scalars",
                                      "commit", "flush", "rollback",
                                      "predict", "embed", "create"]
                        if func_name in suspicious:
                            if not any(parent is child for parent in ast.walk(node)
                                      if isinstance(parent, ast.Await)):
                                # 检查是否在 await 上下文中
                                for parent_node in ast.walk(node):
                                    for child_of_parent in ast.walk(parent_node):
                                        if child_of_parent is child:
                                            if isinstance(parent_node, ast.Await):
                                                break
                                else:
                                    issues.append(f"[AWAIT] {rel}:{ast.get_source_segment(source, child) or func_name} 可能缺少 await")

    # 输出结果
    if issues:
        for issue in issues:
            print(issue)
    else:
        print("OK: 未发现明显问题")
