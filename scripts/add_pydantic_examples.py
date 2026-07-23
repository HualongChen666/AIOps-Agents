# -*- coding: utf-8 -*-
import ast
import os

import astor

EXAMPLE_VALUES = {
    "str": "example",
    "int": 0,
    "float": 0.0,
    "bool": True,
    "list": [],
    "dict": {},
    "Any": None,
}


def infer_example(annotation: str):
    ann = annotation.replace(" ", "")
    if ann.startswith("list") or ann.startswith("List"):
        return []
    if ann.startswith("dict") or ann.startswith("Dict"):
        return {}
    for typ, ex in EXAMPLE_VALUES.items():
        if typ in ann:
            return ex
    return None


def generate_example(fields):
    return {name: infer_example(ann) for name, ann in fields.items()}


def is_base_model(b):
    # supports Name or Attribute or Subscript with Name
    if isinstance(b, ast.Name):
        return b.id == "BaseModel"
    if isinstance(b, ast.Attribute):
        return b.attr == "BaseModel"
    if isinstance(b, ast.Subscript):
        # e.g., BaseModel[Foo]
        return is_base_model(b.value)
    return False


def process_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        source = f.read()
    tree = ast.parse(source)
    modified = False
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            if not any(is_base_model(b) for b in node.bases):
                continue
            # collect fields
            fields = {}
            for stmt in node.body:
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                    field_name = stmt.target.id
                    ann = ast.unparse(stmt.annotation) if hasattr(ast, "unparse") else ""
                    fields[field_name] = ann
            # skip if no fields
            if not fields:
                continue
            # check existing Config
            if any(isinstance(s, ast.ClassDef) and s.name == "Config" for s in node.body):
                continue
            example_dict = generate_example(fields)
            # Build Config class
            config_body = [
                ast.Assign(
                    targets=[ast.Name(id="schema_extra", ctx=ast.Store())],
                    value=ast.Dict(
                        keys=[ast.Constant(value="example")],
                        values=[ast.parse(repr(example_dict)).body[0].value],
                    ),
                )
            ]
            config_class = ast.ClassDef(
                name="Config", bases=[], keywords=[], body=config_body, decorator_list=[]
            )
            node.body.append(config_class)
            modified = True
    if modified:
        new_code = astor.to_source(tree)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_code)
        print(f"Updated {filepath}")


if __name__ == "__main__":
    root = r"C:\AIOps_Agent_bak"
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.endswith(".py"):
                process_file(os.path.join(dirpath, fn))
