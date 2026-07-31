# -*- coding: utf-8 -*-
import ast
import pathlib
import shutil
import subprocess

ROOT = pathlib.Path(r"C:\\AIOps_Agent_bak")


def run_black(file_path: pathlib.Path):
    try:
        cmd = shutil.which("black")
        if not cmd:
            raise FileNotFoundError("black not found")
        subprocess.run([cmd, str(file_path)], check=True, capture_output=True)
    except Exception as e:
        print(f"Black failed on {file_path}: {e}")


def check_and_report(file_path: pathlib.Path):
    try:
        ast.parse(file_path.read_text(encoding="utf-8"))
    except SyntaxError as e:
        print(f"SyntaxError in {file_path}: line {e.lineno}, offset {e.offset}, msg: {e.msg}")
        # 尝试使用 autopep8 自动修复（仅限可修复的格式问题）
        try:
            cmd = shutil.which("autopep8")
            if not cmd:
                raise FileNotFoundError("autopep8 not found")
            subprocess.run(
                [cmd, "--in-place", "--aggressive", "--aggressive", str(file_path)],
                check=True,
                capture_output=True,
            )
            # 再次检查
            ast.parse(file_path.read_text(encoding="utf-8"))
        except Exception as inner:
            print(f"Auto-fix failed for {file_path}: {inner}")
        else:
            print(f"Auto-fix succeeded for {file_path}")


if __name__ == "__main__":
    py_files = list(ROOT.rglob("*.py"))
    for py in py_files:
        # 首先统一编码声明
        text = py.read_text(encoding="utf-8")
        if not text.lstrip().startswith("# -*- coding: utf-8 -*-"):
            py.write_text("# -*- coding: utf-8 -*-\n" + text, encoding="utf-8")
        # 运行 black 格式化
        run_black(py)
        # 检查语法错误并尝试自动修复
        check_and_report(py)
    print("Syntax fixing process completed.")
