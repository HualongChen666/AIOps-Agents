"""
Code Analyzer Module
Provides comprehensive code analysis capabilities including style checking,
type checking, quality checking, security analysis, complexity analysis, and
duplication detection.
"""

import ast
import os
import subprocess
import tempfile
import shutil
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import re


@dataclass
class Issue:
    """Represents a code issue found during analysis."""
    file_path: str
    line: int
    column: int
    code: str
    severity: str
    message: str
    category: str


@dataclass
class CheckResult:
    """Represents the result of a code check."""
    passed: bool
    error_count: int
    warning_count: int
    issues: List[Issue]
    score: float


class CodeAnalyzer:
    """Main code analyzer class that orchestrates various code quality checks."""
    
    def __init__(self):
        self.temp_dir = None
        self._create_temp_dir()
    
    def _create_temp_dir(self):
        """Create a temporary directory for analysis files."""
        self.temp_dir = tempfile.mkdtemp(prefix='code_quality_')
    
    def _cleanup_temp_dir(self):
        """Clean up temporary directory."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def _write_code_to_file(self, code: str, filename: str) -> str:
        """Write code to a temporary file and return the file path."""
        file_path = os.path.join(self.temp_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(code)
        return file_path
    
    def analyze_code(self, code: str, file_path: str = "temp.py", 
                     checkers: List[str] = None) -> Dict[str, Any]:
        """
        Perform comprehensive code analysis using specified checkers.
        
        Args:
            code: The source code to analyze
            file_path: Original file path (for reporting)
            checkers: List of checkers to use (flake8, mypy, pylint, bandit, complexity, duplication)
        
        Returns:
            Dictionary containing analysis results
        """
        if checkers is None:
            checkers = ['flake8', 'mypy', 'pylint', 'bandit', 'complexity', 'duplication']
        
        results = {}
        temp_file = self._write_code_to_file(code, file_path)
        
        try:
            if 'flake8' in checkers:
                results['flake8'] = self.check_flake8(temp_file, file_path)
            
            if 'mypy' in checkers:
                results['mypy'] = self.check_mypy(temp_file, file_path)
            
            if 'pylint' in checkers:
                results['pylint'] = self.check_pylint(temp_file, file_path)
            
            if 'bandit' in checkers:
                results['bandit'] = self.check_bandit(temp_file, file_path)
            
            if 'complexity' in checkers:
                results['complexity'] = self.analyze_complexity(code, file_path)
            
            if 'duplication' in checkers:
                results['duplication'] = self.detect_duplication(code, file_path)
            
            # Calculate overall summary
            summary = self._calculate_summary(results)
            results['summary'] = summary
            
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        
        return results
    
    def check_flake8(self, file_path: str, original_path: str) -> CheckResult:
        """
        Check code style using flake8.
        
        Args:
            file_path: Path to the file to check
            original_path: Original file path for reporting
        
        Returns:
            CheckResult with flake8 findings
        """
        issues = []
        try:
            result = subprocess.run(
                ['flake8', file_path, '--max-line-length=120', '--ignore=E501,W503'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        issue = self._parse_flake8_line(line, original_path)
                        if issue:
                            issues.append(issue)
            
            error_count = sum(1 for i in issues if i.severity == 'error')
            warning_count = sum(1 for i in issues if i.severity == 'warning')
            passed = len(issues) == 0
            score = max(0, 100 - len(issues) * 2)
            
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            # flake8 not available, fallback to basic checks
            issues = self._basic_style_check(file_path, original_path)
            error_count = sum(1 for i in issues if i.severity == 'error')
            warning_count = sum(1 for i in issues if i.severity == 'warning')
            passed = len(issues) == 0
            score = max(0, 100 - len(issues) * 2)
        
        return CheckResult(
            passed=passed,
            error_count=error_count,
            warning_count=warning_count,
            issues=issues,
            score=score
        )
    
    def _parse_flake8_line(self, line: str, original_path: str) -> Optional[Issue]:
        """Parse a flake8 output line into an Issue object."""
        # Format: filename:line:column: code message
        parts = line.split(':', 3)
        if len(parts) >= 4:
            try:
                line_num = int(parts[1])
                col_num = int(parts[2].split()[0])
                rest = parts[3].strip()
                code = rest.split()[0]
                message = ' '.join(rest.split()[1:])
                
                # Determine severity based on code
                severity = 'warning'
                if code.startswith('E9') or code.startswith('F'):
                    severity = 'error'
                elif code.startswith('W'):
                    severity = 'warning'
                else:
                    severity = 'info'
                
                return Issue(
                    file_path=original_path,
                    line=line_num,
                    column=col_num,
                    code=code,
                    severity=severity,
                    message=message,
                    category='style'
                )
            except (ValueError, IndexError):
                pass
        return None
    
    def _basic_style_check(self, file_path: str, original_path: str) -> List[Issue]:
        """Perform basic style checks when flake8 is not available."""
        issues = []
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines, 1):
            # Check line length
            if len(line) > 120:
                issues.append(Issue(
                    file_path=original_path,
                    line=i,
                    column=120,
                    code='E501',
                    severity='warning',
                    message=f'Line too long ({len(line)} > 120 characters)',
                    category='style'
                ))
            
            # Check for trailing whitespace
            if line.rstrip() != line.rstrip('\n'):
                issues.append(Issue(
                    file_path=original_path,
                    line=i,
                    column=len(line.rstrip()),
                    code='W291',
                    severity='warning',
                    message='Trailing whitespace',
                    category='style'
                ))
        
        return issues
    
    def check_mypy(self, file_path: str, original_path: str) -> CheckResult:
        """
        Check type annotations using mypy.
        
        Args:
            file_path: Path to the file to check
            original_path: Original file path for reporting
        
        Returns:
            CheckResult with mypy findings
        """
        issues = []
        try:
            result = subprocess.run(
                ['mypy', file_path, '--no-error-summary', '--show-error-codes'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if line and ':' in line:
                        issue = self._parse_mypy_line(line, original_path)
                        if issue:
                            issues.append(issue)
            
            error_count = sum(1 for i in issues if i.severity == 'error')
            warning_count = sum(1 for i in issues if i.severity == 'warning')
            passed = len(issues) == 0
            score = max(0, 100 - len(issues) * 3)
            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # mypy not available, perform basic type checking
            issues = self._basic_type_check(file_path, original_path)
            error_count = sum(1 for i in issues if i.severity == 'error')
            warning_count = sum(1 for i in issues if i.severity == 'warning')
            passed = len(issues) == 0
            score = max(0, 100 - len(issues) * 3)
        
        return CheckResult(
            passed=passed,
            error_count=error_count,
            warning_count=warning_count,
            issues=issues,
            score=score
        )
    
    def _parse_mypy_line(self, line: str, original_path: str) -> Optional[Issue]:
        """Parse a mypy output line into an Issue object."""
        # Format: filename:line: error: message
        parts = line.split(':', 2)
        if len(parts) >= 3:
            try:
                line_num = int(parts[1])
                rest = parts[2].strip()
                
                severity = 'error'
                if rest.startswith('note:'):
                    severity = 'info'
                elif rest.startswith('warning:'):
                    severity = 'warning'
                else:
                    rest = 'error: ' + rest
                
                message = rest.split(':', 1)[1].strip() if ':' in rest else rest
                code = 'TYPE'
                
                return Issue(
                    file_path=original_path,
                    line=line_num,
                    column=0,
                    code=code,
                    severity=severity,
                    message=message,
                    category='type'
                )
            except (ValueError, IndexError):
                pass
        return None
    
    def _basic_type_check(self, file_path: str, original_path: str) -> List[Issue]:
        """Perform basic type checking when mypy is not available."""
        issues = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check for type annotations
                    if not node.returns and node.name != '__init__':
                        issues.append(Issue(
                            file_path=original_path,
                            line=node.lineno,
                            column=node.col_offset,
                            code='TYPE001',
                            severity='info',
                            message=f'Function "{node.name}" missing return type annotation',
                            category='type'
                        ))
                    
                    # Check parameter annotations
                    for arg in node.args.args:
                        if arg.arg != 'self' and not arg.annotation:
                            issues.append(Issue(
                                file_path=original_path,
                                line=node.lineno,
                                column=node.col_offset,
                                code='TYPE002',
                                severity='info',
                                message=f'Parameter "{arg.arg}" in function "{node.name}" missing type annotation',
                                category='type'
                            ))
        except SyntaxError:
            pass
        
        return issues
    
    def check_pylint(self, file_path: str, original_path: str) -> CheckResult:
        """
        Check code quality using pylint.
        
        Args:
            file_path: Path to the file to check
            original_path: Original file path for reporting
        
        Returns:
            CheckResult with pylint findings
        """
        issues = []
        try:
            result = subprocess.run(
                ['pylint', file_path, '--output-format=text', '--disable=C0111,R0903'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if line and ':' in line and not line.startswith('***'):
                        issue = self._parse_pylint_line(line, original_path)
                        if issue:
                            issues.append(issue)
            
            error_count = sum(1 for i in issues if i.severity == 'error')
            warning_count = sum(1 for i in issues if i.severity == 'warning')
            passed = len(issues) == 0
            score = max(0, 100 - len(issues))
            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # pylint not available, perform basic quality checks
            issues = self._basic_quality_check(file_path, original_path)
            error_count = sum(1 for i in issues if i.severity == 'error')
            warning_count = sum(1 for i in issues if i.severity == 'warning')
            passed = len(issues) == 0
            score = max(0, 100 - len(issues))
        
        return CheckResult(
            passed=passed,
            error_count=error_count,
            warning_count=warning_count,
            issues=issues,
            score=score
        )
    
    def _parse_pylint_line(self, line: str, original_path: str) -> Optional[Issue]:
        """Parse a pylint output line into an Issue object."""
        # Format: filename:line: message (code)
        parts = line.split(':', 2)
        if len(parts) >= 3:
            try:
                line_num = int(parts[1])
                message = parts[2].strip()
                
                # Extract code from message
                code_match = re.search(r'\(([A-Z]\d+)\)', message)
                code = code_match.group(1) if code_match else 'PYLINT'
                
                # Determine severity
                severity = 'warning'
                if code.startswith('E'):
                    severity = 'error'
                elif code.startswith('F'):
                    severity = 'error'
                elif code.startswith('W'):
                    severity = 'warning'
                elif code.startswith('C'):
                    severity = 'info'
                elif code.startswith('R'):
                    severity = 'info'
                
                return Issue(
                    file_path=original_path,
                    line=line_num,
                    column=0,
                    code=code,
                    severity=severity,
                    message=message,
                    category='quality'
                )
            except (ValueError, IndexError):
                pass
        return None
    
    def _basic_quality_check(self, file_path: str, original_path: str) -> List[Issue]:
        """Perform basic quality checks when pylint is not available."""
        issues = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check for docstring
                    if not ast.get_docstring(node):
                        issues.append(Issue(
                            file_path=original_path,
                            line=node.lineno,
                            column=node.col_offset,
                            code='C0111',
                            severity='info',
                            message=f'Missing docstring for function "{node.name}"',
                            category='quality'
                        ))
                    
                    # Check function length
                    if hasattr(node, 'end_lineno') and node.end_lineno:
                        func_length = node.end_lineno - node.lineno
                        if func_length > 50:
                            issues.append(Issue(
                                file_path=original_path,
                                line=node.lineno,
                                column=node.col_offset,
                                code='C0302',
                                severity='warning',
                                message=f'Function "{node.name}" is too long ({func_length} lines)',
                                category='quality'
                            ))
        except SyntaxError:
            pass
        
        return issues
    
    def check_bandit(self, file_path: str, original_path: str) -> CheckResult:
        """
        Check for security issues using bandit.
        
        Args:
            file_path: Path to the file to check
            original_path: Original file path for reporting
        
        Returns:
            CheckResult with bandit findings
        """
        issues = []
        try:
            result = subprocess.run(
                ['bandit', '-f', 'json', file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.stdout:
                import json
                try:
                    data = json.loads(result.stdout)
                    if 'results' in data:
                        for item in data['results']:
                            issue = Issue(
                                file_path=original_path,
                                line=item.get('line_number', 0),
                                column=0,
                                code=item.get('test_id', 'SEC'),
                                severity=item.get('issue_severity', 'MEDIUM').lower(),
                                message=item.get('issue_text', ''),
                                category='security'
                            )
                            issues.append(issue)
                except json.JSONDecodeError:
                    pass
            
            error_count = sum(1 for i in issues if i.severity in ['high', 'error'])
            warning_count = sum(1 for i in issues if i.severity in ['medium', 'warning'])
            passed = len(issues) == 0
            score = max(0, 100 - len(issues) * 5)
            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # bandit not available, perform basic security checks
            issues = self._basic_security_check(file_path, original_path)
            error_count = sum(1 for i in issues if i.severity == 'error')
            warning_count = sum(1 for i in issues if i.severity == 'warning')
            passed = len(issues) == 0
            score = max(0, 100 - len(issues) * 5)
        
        return CheckResult(
            passed=passed,
            error_count=error_count,
            warning_count=warning_count,
            issues=issues,
            score=score
        )
    
    def _basic_security_check(self, file_path: str, original_path: str) -> List[Issue]:
        """Perform basic security checks when bandit is not available."""
        issues = []
        dangerous_patterns = {
            r'eval\s*\(': ('SEC101', 'Use of eval() function'),
            r'exec\s*\(': ('SEC102', 'Use of exec() function'),
            r'pickle\.loads': ('SEC103', 'Use of pickle.loads (potential security risk)'),
            r'shell=True': ('SEC104', 'shell=True in subprocess (potential command injection)'),
            r'password\s*=': ('SEC105', 'Hardcoded password detected'),
            r'api_key\s*=': ('SEC106', 'Hardcoded API key detected'),
            r'secret\s*=': ('SEC107', 'Hardcoded secret detected'),
        }
        
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines, 1):
            for pattern, (code, message) in dangerous_patterns.items():
                if re.search(pattern, line):
                    issues.append(Issue(
                        file_path=original_path,
                        line=i,
                        column=0,
                        code=code,
                        severity='warning',
                        message=message,
                        category='security'
                    ))
        
        return issues
    
    def analyze_complexity(self, code: str, file_path: str) -> Dict[str, Any]:
        """
        Analyze code complexity using cyclomatic complexity.
        
        Args:
            code: The source code to analyze
            file_path: Original file path for reporting
        
        Returns:
            Dictionary containing complexity analysis results
        """
        functions = {}
        total_complexity = 0
        max_complexity = 0
        
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    complexity = self._calculate_cyclomatic_complexity(node)
                    nesting_depth = self._calculate_nesting_depth(node)
                    
                    func_info = {
                        'name': node.name,
                        'line': node.lineno,
                        'cyclomatic_complexity': complexity,
                        'lines_of_code': node.end_lineno - node.lineno if node.end_lineno else 0,
                        'parameters': len(node.args.args),
                        'nesting_depth': nesting_depth
                    }
                    
                    functions[node.name] = func_info
                    total_complexity += complexity
                    max_complexity = max(max_complexity, complexity)
        
        except SyntaxError as e:
            return {
                'success': False,
                'message': f'Syntax error: {str(e)}',
                'functions': {},
                'average_complexity': 0,
                'max_complexity': 0,
                'score': 0
            }
        
        average_complexity = total_complexity / len(functions) if functions else 0
        score = max(0, 100 - max_complexity * 2)
        
        return {
            'success': True,
            'message': 'Complexity analysis completed',
            'functions': functions,
            'average_complexity': average_complexity,
            'max_complexity': max_complexity,
            'score': score
        }
    
    def _calculate_cyclomatic_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity for a function."""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, (ast.And, ast.Or)):
                complexity += 1
        
        return complexity
    
    def _calculate_nesting_depth(self, node: ast.FunctionDef) -> int:
        """Calculate maximum nesting depth for a function."""
        max_depth = 0
        
        def count_depth(n, current_depth=0):
            nonlocal max_depth
            max_depth = max(max_depth, current_depth)
            
            for child in ast.iter_child_nodes(n):
                if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor, 
                                      ast.With, ast.AsyncWith, ast.Try)):
                    count_depth(child, current_depth + 1)
                else:
                    count_depth(child, current_depth)
        
        count_depth(node)
        return max_depth
    
    def detect_duplication(self, code: str, file_path: str, min_lines: int = 5) -> Dict[str, Any]:
        """
        Detect code duplication using token-based analysis.
        
        Args:
            code: The source code to analyze
            file_path: Original file path for reporting
            min_lines: Minimum lines for duplication detection
        
        Returns:
            Dictionary containing duplication detection results
        """
        duplications = []
        lines = code.split('\n')
        
        # Normalize lines for comparison
        normalized_lines = [self._normalize_line(line) for line in lines]
        
        # Find duplicate blocks
        for i in range(len(lines) - min_lines + 1):
            block1 = normalized_lines[i:i + min_lines]
            
            for j in range(i + min_lines, len(lines) - min_lines + 1):
                block2 = normalized_lines[j:j + min_lines]
                
                if block1 == block2 and block1:
                    similarity = 1.0
                    duplications.append({
                        'fragment1': '\n'.join(lines[i:i + min_lines]),
                        'fragment2': '\n'.join(lines[j:j + min_lines]),
                        'lines': min_lines,
                        'start_line1': i + 1,
                        'start_line2': j + 1,
                        'similarity': similarity
                    })
        
        # Calculate duplication rate
        total_lines = len(lines)
        duplicated_lines = sum(d['lines'] for d in duplications)
        duplication_rate = duplicated_lines / total_lines if total_lines > 0 else 0
        score = max(0, 100 - duplication_rate * 100)
        
        return {
            'success': True,
            'message': 'Duplication detection completed',
            'duplications': duplications,
            'duplication_rate': duplication_rate,
            'score': score
        }
    
    def _normalize_line(self, line: str) -> str:
        """Normalize a line for duplication comparison."""
        # Remove comments
        line = re.sub(r'#.*$', '', line)
        # Remove extra whitespace
        line = ' '.join(line.split())
        # Convert to lowercase for case-insensitive comparison
        return line.lower().strip()
    
    def _calculate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall quality summary from individual results."""
        total_issues = 0
        critical_issues = 0
        major_issues = 0
        minor_issues = 0
        checker_scores = {}
        
        for checker, result in results.items():
            if isinstance(result, CheckResult):
                total_issues += len(result.issues)
                critical_issues += sum(1 for i in result.issues if i.severity == 'error')
                major_issues += sum(1 for i in result.issues if i.severity == 'warning')
                minor_issues += sum(1 for i in result.issues if i.severity == 'info')
                checker_scores[checker] = result.score
            elif isinstance(result, dict) and 'score' in result:
                checker_scores[checker] = result['score']
        
        # Calculate overall score
        overall_score = sum(checker_scores.values()) / len(checker_scores) if checker_scores else 100
        
        return {
            'overall_score': overall_score,
            'total_issues': total_issues,
            'critical_issues': critical_issues,
            'major_issues': major_issues,
            'minor_issues': minor_issues,
            'checker_scores': checker_scores
        }
    
    def __del__(self):
        """Clean up temporary directory on deletion."""
        self._cleanup_temp_dir()
