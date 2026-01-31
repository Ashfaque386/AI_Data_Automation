"""
Formula Evaluator Service

Evaluates Excel-like formulas on dataset rows.
Supports mathematical operations and Excel functions.
"""
import re
import math
from typing import Any, Dict, List, Optional
from datetime import datetime, date
from .formula_parser import FormulaParser


class FormulaEvaluator:
    """Evaluator for Excel-like formulas."""
    
    @classmethod
    def evaluate(
        cls,
        formula: str,
        row_data: Dict[str, Any],
        all_rows: Optional[List[Dict[str, Any]]] = None
    ) -> Any:
        """
        Evaluate a formula for a single row.
        
        Args:
            formula: Formula string starting with =
            row_data: Dictionary of column values for current row
            all_rows: All rows (needed for aggregation functions)
            
        Returns:
            Computed value
            
        Raises:
            ValueError: If formula is invalid or evaluation fails
        """
        # Parse formula
        parsed = FormulaParser.parse(formula)
        if not parsed.is_valid:
            raise ValueError(f"Invalid formula: {parsed.error}")
        
        # Remove leading =
        formula_body = formula[1:].strip()
        
        # Replace column references with values
        formula_eval = cls._replace_column_references(formula_body, row_data)
        
        # Replace function calls
        formula_eval = cls._replace_functions(formula_eval, row_data, all_rows)
        
        try:
            # Evaluate the expression
            result = cls._safe_eval(formula_eval)
            return result
        except Exception as e:
            raise ValueError(f"Formula evaluation error: {str(e)}")
    
    @classmethod
    def _replace_column_references(cls, formula: str, row_data: Dict[str, Any]) -> str:
        """Replace [ColumnName] with actual values."""
        def replace_ref(match):
            col_name = match.group(1)
            value = row_data.get(col_name)
            
            # Handle None/null
            if value is None:
                return "None"
            
            # Handle strings - escape and quote
            if isinstance(value, str):
                escaped = value.replace("'", "\\'")
                return f"'{escaped}'"
            
            # Handle booleans
            if isinstance(value, bool):
                return str(value)
            
            # Handle numbers
            return str(value)
        
        return FormulaParser.COLUMN_PATTERN.sub(replace_ref, formula)
    
    @classmethod
    def _replace_functions(
        cls,
        formula: str,
        row_data: Dict[str, Any],
        all_rows: Optional[List[Dict[str, Any]]]
    ) -> str:
        """Replace Excel functions with Python equivalents."""
        # Process functions from innermost to outermost
        max_iterations = 50  # Prevent infinite loops
        iteration = 0
        
        while iteration < max_iterations:
            # Find the innermost function call
            match = re.search(r'([A-Z]+)\s*\(([^()]*)\)', formula)
            if not match:
                break
            
            func_name = match.group(1).upper()
            args_str = match.group(2)
            
            # Evaluate the function
            result = cls._evaluate_function(func_name, args_str, row_data, all_rows)
            
            # Replace function call with result
            formula = formula[:match.start()] + str(result) + formula[match.end():]
            iteration += 1
        
        return formula
    
    @classmethod
    def _evaluate_function(
        cls,
        func_name: str,
        args_str: str,
        row_data: Dict[str, Any],
        all_rows: Optional[List[Dict[str, Any]]]
    ) -> Any:
        """Evaluate a single function call."""
        # Split arguments (simple split by comma - doesn't handle nested commas)
        args = [arg.strip() for arg in args_str.split(',') if arg.strip()]
        
        # Evaluate each argument
        eval_args = []
        for arg in args:
            try:
                # Try to evaluate as expression
                val = cls._safe_eval(arg)
                eval_args.append(val)
            except:
                # Keep as string if evaluation fails
                eval_args.append(arg)
        
        # Mathematical functions
        if func_name == 'SUM':
            return cls._func_sum(eval_args, all_rows)
        elif func_name == 'AVERAGE':
            return cls._func_average(eval_args, all_rows)
        elif func_name == 'MIN':
            return cls._func_min(eval_args, all_rows)
        elif func_name == 'MAX':
            return cls._func_max(eval_args, all_rows)
        elif func_name == 'ROUND':
            return cls._func_round(eval_args)
        elif func_name == 'ABS':
            return abs(eval_args[0]) if eval_args else 0
        elif func_name == 'CEILING':
            return math.ceil(eval_args[0]) if eval_args else 0
        elif func_name == 'FLOOR':
            return math.floor(eval_args[0]) if eval_args else 0
        
        # Logical functions
        elif func_name == 'IF':
            return cls._func_if(eval_args)
        elif func_name == 'AND':
            return all(eval_args)
        elif func_name == 'OR':
            return any(eval_args)
        elif func_name == 'NOT':
            return not eval_args[0] if eval_args else True
        
        # Text functions
        elif func_name == 'CONCAT':
            return ''.join(str(arg) for arg in eval_args)
        elif func_name == 'UPPER':
            return str(eval_args[0]).upper() if eval_args else ""
        elif func_name == 'LOWER':
            return str(eval_args[0]).lower() if eval_args else ""
        elif func_name == 'LEFT':
            return str(eval_args[0])[:int(eval_args[1])] if len(eval_args) >= 2 else ""
        elif func_name == 'RIGHT':
            return str(eval_args[0])[-int(eval_args[1]):] if len(eval_args) >= 2 else ""
        elif func_name == 'LEN':
            return len(str(eval_args[0])) if eval_args else 0
        elif func_name == 'TRIM':
            return str(eval_args[0]).strip() if eval_args else ""
        
        # Aggregation functions
        elif func_name == 'COUNT':
            return cls._func_count(eval_args, all_rows)
        elif func_name == 'COUNTIF':
            return cls._func_countif(eval_args, all_rows)
        
        # Date functions
        elif func_name == 'NOW':
            return datetime.now().isoformat()
        elif func_name == 'TODAY':
            return date.today().isoformat()
        
        else:
            raise ValueError(f"Unsupported function: {func_name}")
    
    @staticmethod
    def _func_sum(args: List[Any], all_rows: Optional[List[Dict[str, Any]]]) -> float:
        """SUM function."""
        if not args:
            return 0
        
        # If single argument is a list/column reference
        if len(args) == 1 and isinstance(args[0], (list, tuple)):
            values = args[0]
        else:
            values = args
        
        total = 0
        for val in values:
            if isinstance(val, (int, float)):
                total += val
        return total
    
    @staticmethod
    def _func_average(args: List[Any], all_rows: Optional[List[Dict[str, Any]]]) -> float:
        """AVERAGE function."""
        if not args:
            return 0
        
        if len(args) == 1 and isinstance(args[0], (list, tuple)):
            values = args[0]
        else:
            values = args
        
        numeric_values = [v for v in values if isinstance(v, (int, float))]
        return sum(numeric_values) / len(numeric_values) if numeric_values else 0
    
    @staticmethod
    def _func_min(args: List[Any], all_rows: Optional[List[Dict[str, Any]]]) -> Any:
        """MIN function."""
        if not args:
            return None
        
        if len(args) == 1 and isinstance(args[0], (list, tuple)):
            values = args[0]
        else:
            values = args
        
        numeric_values = [v for v in values if isinstance(v, (int, float))]
        return min(numeric_values) if numeric_values else None
    
    @staticmethod
    def _func_max(args: List[Any], all_rows: Optional[List[Dict[str, Any]]]) -> Any:
        """MAX function."""
        if not args:
            return None
        
        if len(args) == 1 and isinstance(args[0], (list, tuple)):
            values = args[0]
        else:
            values = args
        
        numeric_values = [v for v in values if isinstance(v, (int, float))]
        return max(numeric_values) if numeric_values else None
    
    @staticmethod
    def _func_round(args: List[Any]) -> float:
        """ROUND function."""
        if not args:
            return 0
        
        value = args[0]
        decimals = int(args[1]) if len(args) > 1 else 0
        return round(float(value), decimals)
    
    @staticmethod
    def _func_if(args: List[Any]) -> Any:
        """IF function."""
        if len(args) < 2:
            return None
        
        condition = args[0]
        true_value = args[1]
        false_value = args[2] if len(args) > 2 else None
        
        return true_value if condition else false_value
    
    @staticmethod
    def _func_count(args: List[Any], all_rows: Optional[List[Dict[str, Any]]]) -> int:
        """COUNT function."""
        if not args:
            return 0
        
        if len(args) == 1 and isinstance(args[0], (list, tuple)):
            values = args[0]
        else:
            values = args
        
        return len([v for v in values if v is not None])
    
    @staticmethod
    def _func_countif(args: List[Any], all_rows: Optional[List[Dict[str, Any]]]) -> int:
        """COUNTIF function - simplified version."""
        if len(args) < 2:
            return 0
        
        values = args[0] if isinstance(args[0], (list, tuple)) else [args[0]]
        condition = args[1]
        
        # Simple equality check
        return len([v for v in values if v == condition])
    
    @staticmethod
    def _safe_eval(expression: str) -> Any:
        """
        Safely evaluate a mathematical expression.
        Only allows basic arithmetic operations.
        """
        # Remove whitespace
        expression = expression.strip()
        
        # Handle None
        if expression == "None":
            return None
        
        # Handle booleans
        if expression == "True":
            return True
        if expression == "False":
            return False
        
        # Handle strings (quoted)
        if expression.startswith("'") and expression.endswith("'"):
            return expression[1:-1]
        
        # Allowed characters for safe evaluation
        allowed_chars = set("0123456789+-*/().%^ ")
        if not all(c in allowed_chars or c.isspace() for c in expression):
            # If contains other characters, return as string
            return expression
        
        try:
            # Replace ^ with ** for exponentiation
            expression = expression.replace('^', '**')
            
            # Use eval with restricted globals/locals
            result = eval(expression, {"__builtins__": {}}, {})
            return result
        except:
            # If evaluation fails, return as string
            return expression
