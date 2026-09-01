"""Read-only tool primitives and authorization."""

from __future__ import annotations

from enum import StrEnum


class ToolPermission(StrEnum):
    READ = "read"
    WRITE = "write"


class ToolAuthorizationError(PermissionError):
    pass


class ReadOnlyTool:
    permission = ToolPermission.READ

    def authorize(self, requested: ToolPermission) -> None:
        if requested is not ToolPermission.READ:
            raise ToolAuthorizationError(f"Tool only permits {ToolPermission.READ.value} operations")
