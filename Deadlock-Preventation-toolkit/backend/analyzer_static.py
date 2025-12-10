import ast
from collections import defaultdict
from typing import Dict, List, Any

def analyze_python_source(code: str) -> Dict[str, Any]:
    """
    Simple static analyzer for Python source using ast.
    Returns functions, global variable assignments, and lock calls.
    """
    try:
        tree = ast.parse(code)
    except Exception as e:
        return {"error": f"Parse error: {e}"}

    funcs: List[str] = []
    global_vars = defaultdict(list)
    lock_calls: List[Dict[str, Any]] = []

    class Analyzer(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            funcs.append(node.name)
            self.generic_visit(node)

        def visit_Assign(self, node):
            if node.targets and isinstance(node.targets[0], ast.Name):
                global_vars[node.targets[0].id].append(
                    (node.lineno, node.col_offset)
                )
            self.generic_visit(node)

        def visit_Call(self, node):
            if isinstance(node.func, ast.Attribute):
                attr = node.func.attr
                if attr in ("acquire", "release", "lock"):
                    obj = getattr(node.func.value, "id",
                                  getattr(node.func.value, "attr",
                                          repr(node.func.value)))
                    lock_calls.append({
                        "call": attr,
                        "object": obj,
                        "lineno": node.lineno
                    })
            self.generic_visit(node)

    Analyzer().visit(tree)

    return {
        "language": "python",
        "functions": funcs,
        "global_assignments": dict(global_vars),
        "lock_calls": lock_calls
    }
