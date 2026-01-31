"""
Formula Parser Service

Parses Excel-like formulas and extracts dependencies.
Supports column references using [ColumnName] syntax.
"""
import re
from typing import List, Dict, Set, Any, Optional
from dataclasses import dataclass


@dataclass
class ParsedFormula:
    """Represents a parsed formula with its components."""
    original: str
    normalized: str
    dependencies: Set[str]
    functions: Set[str]
    is_valid: bool
    error: Optional[str] = None


class FormulaParser:
    """Parser for Excel-like formulas."""
    
    # Supported Excel functions
    SUPPORTED_FUNCTIONS = {
        # Mathematical
        'SUM', 'AVERAGE', 'MIN', 'MAX', 'ROUND', 'ABS', 'CEILING', 'FLOOR',
        # Logical
        'IF', 'AND', 'OR', 'NOT',
        # Text
        'CONCAT', 'UPPER', 'LOWER', 'LEFT', 'RIGHT', 'LEN', 'TRIM',
        # Aggregation
        'COUNT', 'COUNTIF',
        # Date (basic)
        'NOW', 'TODAY', 'YEAR', 'MONTH', 'DAY'
    }
    
    # Pattern to match column references: [ColumnName]
    COLUMN_PATTERN = re.compile(r'\[([^\]]+)\]')
    
    # Pattern to match function calls: FUNCTION(...)
    FUNCTION_PATTERN = re.compile(r'([A-Z]+)\s*\(')
    
    @classmethod
    def parse(cls, formula: str) -> ParsedFormula:
        """
        Parse a formula and extract its components.
        
        Args:
            formula: Formula string starting with =
            
        Returns:
            ParsedFormula object with parsed components
        """
        if not formula or not isinstance(formula, str):
            return ParsedFormula(
                original=formula or "",
                normalized="",
                dependencies=set(),
                functions=set(),
                is_valid=False,
                error="Formula cannot be empty"
            )
        
        # Formula must start with =
        if not formula.startswith('='):
            return ParsedFormula(
                original=formula,
                normalized="",
                dependencies=set(),
                functions=set(),
                is_valid=False,
                error="Formula must start with '='"
            )
        
        # Remove leading =
        formula_body = formula[1:].strip()
        
        # Extract column dependencies
        dependencies = set(cls.COLUMN_PATTERN.findall(formula_body))
        
        # Extract function calls
        functions = set(cls.FUNCTION_PATTERN.findall(formula_body.upper()))
        
        # Validate functions
        invalid_functions = functions - cls.SUPPORTED_FUNCTIONS
        if invalid_functions:
            return ParsedFormula(
                original=formula,
                normalized="",
                dependencies=dependencies,
                functions=functions,
                is_valid=False,
                error=f"Unsupported functions: {', '.join(invalid_functions)}"
            )
        
        # Check balanced parentheses
        if not cls._check_balanced_parentheses(formula_body):
            return ParsedFormula(
                original=formula,
                normalized="",
                dependencies=dependencies,
                functions=functions,
                is_valid=False,
                error="Unbalanced parentheses"
            )
        
        # Normalize formula (for comparison/storage)
        normalized = cls._normalize_formula(formula_body)
        
        return ParsedFormula(
            original=formula,
            normalized=normalized,
            dependencies=dependencies,
            functions=functions,
            is_valid=True,
            error=None
        )
    
    @classmethod
    def validate_dependencies(
        cls, 
        formula: str, 
        available_columns: List[str]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate that all column references exist.
        
        Args:
            formula: Formula to validate
            available_columns: List of available column names
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        parsed = cls.parse(formula)
        
        if not parsed.is_valid:
            return False, parsed.error
        
        available_set = set(available_columns)
        missing = parsed.dependencies - available_set
        
        if missing:
            return False, f"Referenced columns not found: {', '.join(missing)}"
        
        return True, None
    
    @classmethod
    def detect_circular_dependency(
        cls,
        column_name: str,
        formula: str,
        existing_formulas: Dict[str, str]
    ) -> tuple[bool, Optional[List[str]]]:
        """
        Detect circular dependencies in formulas.
        
        Args:
            column_name: Name of the column being added/updated
            formula: Formula for the column
            existing_formulas: Dict of {column_name: formula}
            
        Returns:
            Tuple of (has_cycle, cycle_path)
        """
        parsed = cls.parse(formula)
        if not parsed.is_valid:
            return False, None
        
        # Build dependency graph
        graph: Dict[str, Set[str]] = {}
        
        # Add existing formulas
        for col, form in existing_formulas.items():
            if col != column_name:  # Skip the column being updated
                parsed_existing = cls.parse(form)
                graph[col] = parsed_existing.dependencies
        
        # Add new formula
        graph[column_name] = parsed.dependencies
        
        # Check for cycles using DFS
        def has_cycle_dfs(node: str, visited: Set[str], path: List[str]) -> tuple[bool, Optional[List[str]]]:
            if node in path:
                # Found a cycle
                cycle_start = path.index(node)
                return True, path[cycle_start:] + [node]
            
            if node in visited:
                return False, None
            
            visited.add(node)
            path.append(node)
            
            # Check dependencies
            for dep in graph.get(node, set()):
                if dep in graph:  # Only check if dependency is also a computed column
                    has_cycle, cycle_path = has_cycle_dfs(dep, visited, path[:])
                    if has_cycle:
                        return True, cycle_path
            
            return False, None
        
        return has_cycle_dfs(column_name, set(), [])
    
    @staticmethod
    def _check_balanced_parentheses(formula: str) -> bool:
        """Check if parentheses are balanced."""
        count = 0
        for char in formula:
            if char == '(':
                count += 1
            elif char == ')':
                count -= 1
                if count < 0:
                    return False
        return count == 0
    
    @staticmethod
    def _normalize_formula(formula: str) -> str:
        """Normalize formula for storage/comparison."""
        # Remove extra whitespace
        normalized = ' '.join(formula.split())
        # Convert to uppercase for case-insensitive comparison
        return normalized.upper()
