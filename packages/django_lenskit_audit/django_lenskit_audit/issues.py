from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional

Severity = Literal["info", "warning", "error"]


@dataclass(frozen=True)
class Issue:
    severity: Severity
    code: str
    message: str
    app_label: str
    model_name: str
    hint: Optional[str] = None
    admin_class_path: Optional[str] = None
    details: dict[str, Any] | None = None
