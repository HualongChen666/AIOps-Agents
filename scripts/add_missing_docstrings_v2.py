import ast
import os

ROOT = r"C:\\AIOps_Agent_bak"

placeholder = '"""TODO: Add module docstring (Google style)."""\n'


def ensure_module_docstring(lines):
    # If first non-empty, non-comment line is not a docstring, insert default_value
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith('"""') or stripped.startswith("'''"):
            return lines  # already has module docstring
        # Insert default_value before this line
        return lines[:i] + [placeholder] + lines[i:]
    # file empty => just add default_value


def process_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        source = f.read()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        # skip files with syntax errors (should be none after previous fixes)
        return False
    lines = source.splitlines(keepends=True)
    # Ensure module docstring
    lines = ensure_module_docstring(lines)

    # Walk through classes and funcs
    class Insertor(ast.NodeVisitor):
        def __init__(self, lines):
            self.lines = lines
            self.edits = []  # (lineno, indent, default_value)

        def generic_visit(self, node):
            super().generic_visit(node)

        def visit_FunctionDef(self, node):
            # check if first statement is a docstring
            if not (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Str)
            ):
                indent = " " * (node.col_offset + 4)
                placeholder = f'{indent}"""TODO: Add docstring (Google style)."""\n'
                self.edits.append((node.lineno, indent, placeholder))
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node):
            self.visit_FunctionDef(node)

        def visit_ClassDef(self, node):
            if not (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Str)
            ):
                indent = " " * (node.col_offset + 4)
                placeholder = f'{indent}"""TODO: Add docstring (Google style)."""\n'
                self.edits.append((node.lineno, indent, placeholder))
            self.generic_visit(node)

    inserter = Insertor(lines)
    inserter.visit(tree)
    # Apply edits in reverse order to keep line numbers valid
    for lineno, indent, placeholder in sorted(inserter.edits, reverse=True):
        # Insert after the definition line (lineno is 1-indexed of def line)
        insert_index = lineno  # after the def line
        lines.insert(insert_index, placeholder)
    new_content = "".join(lines)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)
    return True


changed = []
for dirpath, _, filenames in os.walk(ROOT):
    for name in filenames:
        if name.endswith(".py"):
            fp = os.path.join(dirpath, name)
            if process_file(fp):
                changed.append(fp)
print(f"Processed {len(changed)} files")
