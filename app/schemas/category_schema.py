from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Any


FieldType = Literal[
    "text", "textarea", "number", "dropdown",
    "checkbox", "radio", "date", "file",
    "creatable_select", "composite",
]


class CompositeSubField(BaseModel):
    """Defines a sub-field within a composite field."""
    name: str = Field(min_length=1)  # e.g., "Length", "Breadth", "Height"
    field_name: str = Field(min_length=1)  # e.g., "length", "breadth", "height"
    field_type: Literal["number"] = "number"  # Only number type allowed
    is_required: bool = False
    placeholder: Optional[str] = None
    display_order: int = 0


class ValidationRules(BaseModel):
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    pattern: Optional[str] = None
    custom_error_message: Optional[str] = None


class ConditionalLogic(BaseModel):
    show_if_field: Optional[str] = None  # field_id to depend on
    show_if_value: Optional[Any] = None


class FieldDefinition(BaseModel):
    field_id: Optional[str] = None  # auto-generated if not provided
    label: str = Field(min_length=1)
    field_name: str = Field(min_length=1)
    field_type: FieldType
    is_required: bool = False
    placeholder: Optional[str] = None
    default_value: Optional[Any] = None
    options: Optional[List[str]] = None  # for dropdown, radio, checkbox
    validation: Optional[ValidationRules] = None
    display_order: int = 0
    help_text: Optional[str] = None
    conditional_logic: Optional[ConditionalLogic] = None
    sub_fields: Optional[List[CompositeSubField]] = None  # for composite field type


class CategorySchemaCreate(BaseModel):
    name: str = Field(min_length=2)
    group: str = Field(min_length=1)
    description: Optional[str] = None
    fields: List[FieldDefinition] = []


class CategorySchemaUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class FieldsReplacePayload(BaseModel):
    """Replace the entire fields array (used by the builder UI)."""
    fields: List[FieldDefinition]


class ReorderPayload(BaseModel):
    """Reorder fields by providing an ordered list of field_ids."""
    field_order: List[str]
