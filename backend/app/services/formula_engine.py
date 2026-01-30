"""
Formula Engine - Excel-Compatible Formula Processing
"""
import re
import math
from typing import Any, Dict, List, Optional, Tuple, Callable
from datetime import datetime
import pandas as pd
import numpy as np
import structlog

logger = structlog.get_logger()


class FormulaError(Exception):
    """Formula evaluation error."""
    pass


class ExcelFunctions:
    """Excel-compatible function implementations."""
    
    @staticmethod
    def SUM(*args) -> float:
        total = 0
        for arg in args:
            if isinstance(arg, (list, pd.Series, np.ndarray)):
                total += sum(float(x) for x in arg if x is not None and not pd.isna(x))
            elif arg is not None and not pd.isna(arg):
                total += float(arg)
        return total
    
    @staticmethod
    def AVERAGE(*args) -> float:
        values = []
        for arg in args:
            if isinstance(arg, (list, pd.Series, np.ndarray)):
                values.extend(float(x) for x in arg if x is not None and not pd.isna(x))
            elif arg is not None and not pd.isna(arg):
                values.append(float(arg))
        return sum(values) / len(values) if values else 0
    
    @staticmethod
    def COUNT(*args) -> int:
        count = 0
        for arg in args:
            if isinstance(arg, (list, pd.Series, np.ndarray)):
                count += sum(1 for x in arg if isinstance(x, (int, float)) and not pd.isna(x))
            elif isinstance(arg, (int, float)) and not pd.isna(arg):
                count += 1
        return count
    
    @staticmethod
    def MIN(*args) -> float:
        values = []
        for arg in args:
            if isinstance(arg, (list, pd.Series, np.ndarray)):
                values.extend(float(x) for x in arg if not pd.isna(x))
            elif not pd.isna(arg):
                values.append(float(arg))
        return min(values) if values else 0
    
    @staticmethod
    def MAX(*args) -> float:
        values = []
        for arg in args:
            if isinstance(arg, (list, pd.Series, np.ndarray)):
                values.extend(float(x) for x in arg if not pd.isna(x))
            elif not pd.isna(arg):
                values.append(float(arg))
        return max(values) if values else 0
    
    @staticmethod
    def IF(condition: bool, true_val: Any, false_val: Any = "") -> Any:
        return true_val if condition else false_val
    
    @staticmethod
    def AND(*args) -> bool:
        return all(bool(arg) for arg in args)
    
    @staticmethod
    def OR(*args) -> bool:
        return any(bool(arg) for arg in args)
    
    @staticmethod
    def CONCATENATE(*args) -> str:
        return "".join(str(arg) if arg else "" for arg in args)
    
    @staticmethod
    def LEFT(text: str, n: int = 1) -> str:
        return str(text)[:int(n)]
    
    @staticmethod
    def RIGHT(text: str, n: int = 1) -> str:
        return str(text)[-int(n):]
    
    @staticmethod
    def LEN(text: str) -> int:
        return len(str(text))
    
    @staticmethod
    def TRIM(text: str) -> str:
        return str(text).strip()
    
    @staticmethod
    def UPPER(text: str) -> str:
        return str(text).upper()
    
    @staticmethod
    def LOWER(text: str) -> str:
        return str(text).lower()
    
    @staticmethod
    def ROUND(number: float, digits: int = 0) -> float:
        return round(float(number), int(digits))
    
    @staticmethod
    def ABS(number: float) -> float:
        return abs(float(number))
    
    @staticmethod
    def NOW() -> datetime:
        return datetime.now()
    
    @staticmethod
    def TODAY() -> datetime:
        return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    @staticmethod
    def YEAR(date) -> int:
        if isinstance(date, str):
            date = pd.to_datetime(date)
        return date.year
    
    @staticmethod
    def MONTH(date) -> int:
        if isinstance(date, str):
            date = pd.to_datetime(date)
        return date.month
    
    @staticmethod
    def IFERROR(value: Any, error_value: Any) -> Any:
        try:
            if value is None or (isinstance(value, float) and math.isnan(value)):
                return error_value
            return value
        except:
            return error_value


class FormulaEngine:
    """Excel-compatible formula engine."""
    
    def __init__(self):
        self.functions = ExcelFunctions
        self._context: Dict[str, Any] = {}
    
    def _get_function(self, name: str) -> Optional[Callable]:
        return getattr(self.functions, name.upper(), None)
    
    def evaluate(self, formula: str, df: pd.DataFrame = None, 
                 row_context: Dict[str, Any] = None) -> Any:
        """Evaluate a formula."""
        if formula.startswith('='):
            formula = formula[1:]
        self._context = row_context or {}
        try:
            return self._evaluate_expression(formula, df)
        except Exception as e:
            raise FormulaError(f"Formula error: {str(e)}")
    
    def _evaluate_expression(self, expr: str, df: pd.DataFrame = None) -> Any:
        expr = expr.strip()
        
        # Function call
        func_match = re.match(r'^([A-Z_]\w*)\s*\((.*)\)$', expr, re.I | re.DOTALL)
        if func_match:
            func = self._get_function(func_match.group(1))
            if func:
                args = self._parse_arguments(func_match.group(2), df)
                return func(*args)
        
        # Column reference
        if expr in self._context:
            return self._context[expr]
        
        # String literal
        if expr.startswith('"') and expr.endswith('"'):
            return expr[1:-1]
        
        # Number
        try:
            return float(expr) if '.' in expr else int(expr)
        except ValueError:
            pass
        
        # Arithmetic operators
        for op in ['+', '-', '*', '/']:
            if op in expr:
                parts = expr.rsplit(op, 1)
                if len(parts) == 2:
                    l, r = self._evaluate_expression(parts[0], df), self._evaluate_expression(parts[1], df)
                    if op == '+': return float(l) + float(r)
                    if op == '-': return float(l) - float(r)
                    if op == '*': return float(l) * float(r)
                    if op == '/': return float(l) / float(r) if r else 0
        
        return expr
    
    def _parse_arguments(self, args_str: str, df: pd.DataFrame) -> List[Any]:
        args, current, depth = [], "", 0
        for char in args_str:
            if char == '(': depth += 1
            elif char == ')': depth -= 1
            if char == ',' and depth == 0:
                if current.strip():
                    args.append(self._evaluate_expression(current.strip(), df))
                current = ""
            else:
                current += char
        if current.strip():
            args.append(self._evaluate_expression(current.strip(), df))
        return args
    
    def apply_to_column(self, formula: str, df: pd.DataFrame, 
                        result_column: str) -> pd.DataFrame:
        """Apply formula to create a new column."""
        results = []
        for _, row in df.iterrows():
            try:
                results.append(self.evaluate(formula, df, row.to_dict()))
            except:
                results.append(None)
        df_result = df.copy()
        df_result[result_column] = results
        return df_result
    
    def validate_formula(self, formula: str) -> Tuple[bool, str]:
        if formula.startswith('='):
            formula = formula[1:]
        if formula.count('(') != formula.count(')'):
            return False, "Unbalanced parentheses"
        return True, ""
