"""
Template rendering utility for certificate descriptions.
Supports simple variable substitution using {field_name} syntax.
"""
import re
from typing import Dict, Any, Optional


def render_description_template(template: Optional[str], field_values: Dict[str, Any]) -> str:
    """
    Render a description template by replacing {field_name} placeholders with actual values.

    Args:
        template: Template string with placeholders like "One {metal} {category}"
        field_values: Dictionary of field values, e.g., {"metal": "Gold", "category": "Ring"}

    Returns:
        Rendered description string, or empty string if template is None/empty

    Example:
        >>> render_description_template(
        ...     "One {metal} {category} Studded with {diamond_piece} {conclusion}.",
        ...     {"metal": "Gold", "category": "Ring", "diamond_piece": "5", "conclusion": "Natural Diamond"}
        ... )
        "One Gold Ring Studded with 5 Natural Diamond."
    """
    if not template:
        return ""

    # Make a copy to work with
    result = template

    # Find all placeholders in the format {field_name}
    placeholders = re.findall(r'\{([^}]+)\}', template)

    # Replace each placeholder with its value
    for placeholder in placeholders:
        field_name = placeholder.strip()

        # Get value from field_values
        # Support nested objects (e.g., dimension.length)
        value = get_nested_value(field_values, field_name)

        # Convert value to string, handle None/empty
        if value is None or value == "":
            value_str = ""
        elif isinstance(value, (int, float)):
            value_str = str(value)
        elif isinstance(value, dict):
            # For composite fields, try to format nicely
            value_str = format_composite_value(value)
        else:
            value_str = str(value)

        # Replace the placeholder
        result = result.replace(f"{{{field_name}}}", value_str)

    # Clean up extra spaces
    result = re.sub(r'\s+', ' ', result).strip()

    return result


def get_nested_value(data: Dict[str, Any], path: str) -> Any:
    """
    Get value from nested dictionary using dot notation.

    Example:
        >>> get_nested_value({"dimension": {"length": "5.2"}}, "dimension.length")
        "5.2"
    """
    keys = path.split('.')
    value = data

    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            return None

    return value


def format_composite_value(value: Dict[str, Any]) -> str:
    """
    Format composite field values into a readable string.

    Example:
        >>> format_composite_value({"length": "5.2", "width": "5.1", "height": "3.2"})
        "5.2 x 5.1 x 3.2"
    """
    if not isinstance(value, dict):
        return str(value)

    # For dimension fields, format as "L x W x H"
    if all(k in value for k in ['length', 'width', 'height']):
        parts = [value.get('length', ''), value.get('width', ''), value.get('height', '')]
        # Filter out empty values
        parts = [p for p in parts if p]
        return ' x '.join(parts)

    # For other composite fields, join values with comma
    return ', '.join(str(v) for v in value.values() if v)


def get_available_fields(schema_fields: list) -> list:
    """
    Extract field names from schema to show available template variables.

    Args:
        schema_fields: List of field definitions from schema

    Returns:
        List of field names that can be used in templates
    """
    field_names = []

    for field in schema_fields:
        field_name = field.get('field_name')
        if field_name:
            field_names.append(field_name)

            # For composite fields, also add sub-field paths
            if field.get('field_type') == 'composite' and field.get('sub_fields'):
                for sub_field in field['sub_fields']:
                    sub_field_name = sub_field.get('field_name')
                    if sub_field_name:
                        field_names.append(f"{field_name}.{sub_field_name}")

    return sorted(field_names)
