"""检查所有 Python 文件语法"""
import os, sys

root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
errors = []
count = 0

for dirpath, _, filenames in os.walk(root):
    for fn in filenames:
        if fn.endswith(".py"):
            fpath = os.path.join(dirpath, fn)
            count += 1
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    code = f.read()
                compile(code, fpath, "exec")
            except SyntaxError as e:
                errors.append((os.path.relpath(fpath, root), str(e)))
            except Exception as e:
                errors.append((os.path.relpath(fpath, root), str(e)))

if errors:
    for rel, err in errors:
        print(f"FAIL: {rel}")
        print(f"  {err}")
else:
    print(f"OK: all {count} Python files pass syntax check")
