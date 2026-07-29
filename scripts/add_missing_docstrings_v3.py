import ast
import os

PLACEHOLDER = "default_value"

ROOT = r"C:\\AIOps_Agent_bak"


def has_module_docstring(tree):
    """Return True if the module already has a docstring as first stmt."""
    if not tree.body:
        return False
    first = tree.body[0]
    return isinstance(first, ast.Expr) and isinstance(first.value, (ast.Str, ast.Constant))


def insert_module_docstring(lines):
    """Insert default_value module docstring after any shebang/encoding lines.
    Returns new list of lines.
    """
    insert_idx = 0
    # skip shebang or encoding comment at top
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if (
            stripped.startswith("#!")
            or stripped.startswith("# -*-")
            or stripped.startswith("# coding")
        ):
            continue
        # first non-shebang/non-encoding line
        insert_idx = i
        break
    placeholder_line = f"{PLACEHOLDER}\n"
    return lines[:insert_idx] + [placeholder_line] + lines[insert_idx:]


def process_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        source = f.read()
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        print(f"[SKIP] SyntaxError in {filepath}: {e}")
        return False
    lines = source.splitlines(keepends=True)
    # 1) Ensure module docstring
    if not has_module_docstring(tree):
        lines = insert_module_docstring(lines)
    # 2) Collect insert positions for functions/classes lacking docstring
    edits = []  # (lineno (1-indexed), indent_str)

    class Visitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            if ast.get_docstring(node) is None:
                indent = " " * (node.col_offset + 4)
                edits.append((node.lineno, indent))
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node):
            self.visit_FunctionDef(node)

        def visit_ClassDef(self, node):
            if ast.get_docstring(node) is None:
                indent = " " * (node.col_offset + 4)
                edits.append((node.lineno, indent))
            self.generic_visit(node)

    Visitor().visit(tree)
    # Apply edits in reverse order to keep indices valid
    for lineno, indent in sorted(edits, reverse=True):
        insert_idx = lineno  # after the line with def/class (0‑based index = lineno)
        placeholder_line = f"{indent}{PLACEHOLDER}\n"
        lines.insert(insert_idx, placeholder_line)
    new_content = "".join(lines)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)
    return True


if __name__ == "__main__":
    changed = []
    for dirpath, _, filenames in os.walk(ROOT):
        for name in filenames:
            if name.endswith(".py"):
                fp = os.path.join(dirpath, name)
                if process_file(fp):
                    changed.append(fp)
    print(f"Processed {len(changed)} python files.")
