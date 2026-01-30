"""Custom exceptions for the data ingestion pipeline."""

from typing import Any


class IngestionError(Exception):
    """Base exception for all ingestion-related errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class ValidationError(IngestionError):
    """Data validation error."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: Any = None,
        constraint: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.field = field
        self.value = value
        self.constraint = constraint

    def __str__(self) -> str:
        parts = [self.message]
        if self.field:
            parts.append(f"Field: {self.field}")
        if self.value is not None:
            parts.append(f"Value: {self.value}")
        if self.constraint:
            parts.append(f"Constraint: {self.constraint}")
        return " | ".join(parts)


class MappingError(IngestionError):
    """ID mapping error."""

    def __init__(
        self,
        message: str,
        entity_type: str | None = None,
        external_id: str | None = None,
        mapping_table: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.entity_type = entity_type
        self.external_id = external_id
        self.mapping_table = mapping_table

    def __str__(self) -> str:
        parts = [self.message]
        if self.entity_type:
            parts.append(f"Entity: {self.entity_type}")
        if self.external_id:
            parts.append(f"External ID: {self.external_id}")
        if self.mapping_table:
            parts.append(f"Mapping Table: {self.mapping_table}")
        return " | ".join(parts)


class DatabaseError(IngestionError):
    """Database operation error."""

    def __init__(
        self,
        message: str,
        operation: str | None = None,
        query: str | None = None,
        original_error: Exception | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.operation = operation
        self.query = query
        self.original_error = original_error

    def __str__(self) -> str:
        parts = [self.message]
        if self.operation:
            parts.append(f"Operation: {self.operation}")
        if self.original_error:
            parts.append(f"Original Error: {self.original_error}")
        return " | ".join(parts)


class FileError(IngestionError):
    """File operation error."""

    def __init__(
        self,
        message: str,
        file_path: str | None = None,
        operation: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.file_path = file_path
        self.operation = operation

    def __str__(self) -> str:
        parts = [self.message]
        if self.file_path:
            parts.append(f"File: {self.file_path}")
        if self.operation:
            parts.append(f"Operation: {self.operation}")
        return " | ".join(parts)


class ETLError(IngestionError):
    """ETL process error."""

    def __init__(
        self,
        message: str,
        etl_stage: str | None = None,
        entity_type: str | None = None,
        original_error: Exception | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.etl_stage = etl_stage
        self.entity_type = entity_type
        self.original_error = original_error

    def __str__(self) -> str:
        parts = [self.message]
        if self.etl_stage:
            parts.append(f"Stage: {self.etl_stage}")
        if self.entity_type:
            parts.append(f"Entity: {self.entity_type}")
        if self.original_error:
            parts.append(f"Original Error: {self.original_error}")
        return " | ".join(parts)


class APIError(IngestionError):
    """API call error."""

    def __init__(
        self,
        message: str,
        endpoint: str | None = None,
        status_code: int | None = None,
        original_error: Exception | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.endpoint = endpoint
        self.status_code = status_code
        self.original_error = original_error

    def __str__(self) -> str:
        parts = [self.message]
        if self.endpoint:
            parts.append(f"Endpoint: {self.endpoint}")
        if self.status_code:
            parts.append(f"Status Code: {self.status_code}")
        if self.original_error:
            parts.append(f"Original Error: {self.original_error}")
        return " | ".join(parts)


class DataTransformationError(IngestionError):
    """Data transformation error."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: Any = None,
        transformation: str | None = None,
        original_error: Exception | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.field = field
        self.value = value
        self.transformation = transformation
        self.original_error = original_error

    def __str__(self) -> str:
        parts = [self.message]
        if self.field:
            parts.append(f"Field: {self.field}")
        if self.value is not None:
            parts.append(f"Value: {self.value}")
        if self.transformation:
            parts.append(f"Transformation: {self.transformation}")
        if self.original_error:
            parts.append(f"Original Error: {self.original_error}")
        return " | ".join(parts)
