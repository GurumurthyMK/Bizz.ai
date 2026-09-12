"""Service-layer errors. Routes translate these into HTTP responses."""

from dataclasses import dataclass


@dataclass
class NotFoundError(Exception):
    entity: str
    identifier: int | str

    def __str__(self) -> str:
        return f"{self.entity} {self.identifier} not found."


@dataclass
class ReferenceError(Exception):
    """A create/update references a related record that does not exist."""

    entity: str
    identifier: int | str

    def __str__(self) -> str:
        return f"{self.entity} {self.identifier} not found."


@dataclass
class ConflictError(Exception):
    detail: str

    def __str__(self) -> str:
        return self.detail
