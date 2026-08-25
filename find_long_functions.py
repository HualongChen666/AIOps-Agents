#!/usr/bin/env python3
"""Script to identify functions longer than 50 lines."""
import ast
import os
from pathlib import Path
from typing import List, Tuple, Dict

def count_lines(node: ast.AST) -> int:
    """Count the number of lines in an AST node."""
    if hasattr(node, 'end_lineno') and hasattr(node, 'lineno'):
        return node.end_lineno - node.lineno + 1
    return 0

def find_long_functions(file_path: Path) -> List[Tuple[str, int, int]]:
    """Find functions longer than 50 lines in a file."""
    long_functions = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content, filename=str(file_path))
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                line_count = count_lines(node)
                if line_count > 50:
                    long_functions.append((node.name, node.lineno, line_count))
    except Exception as e:
        pass  # Skip files that can't be parsed
    
    return long_functions

def main():
    """Main function to scan the codebase."""
    results = {}
    
    # Scan common Python directories
    directories = ['api', 'core', 'services', 'modules', 'aiops_agent', 'models']
    
    for directory in directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            continue
            
        for py_file in dir_path.rglob('*.py'):
            long_funcs = find_long_functions(py_file)
            if long_funcs:
                results[str(py_file)] = long_funcs
    
    # Print results
    print("Long Functions (>50 lines):")
    print("=" * 80)
    for file_path, functions in sorted(results.items()):
        print(f"\n{file_path}:")
        for func_name, line_no, line_count in functions:
            print(f"  - {func_name} (line {line_no}, {line_count} lines)")
    
    # Summary
    total = sum(len(funcs) for funcs in results.values())
    print(f"\n\nTotal long functions found: {total}")

if __name__ == '__main__':
    main()
