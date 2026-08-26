"""DeliveryPlan / TaskUnit 数据模型（对标 ai-ppt Outline + Slide 单元）。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from app.llm.unit_flow.merge import FillMergeResult


class UnitKind(str, Enum):
    island_labels = "island_labels"
    island_seeds = "island_seeds"
    island_entities = "island_entities"
    island_roles = "island_roles"
    er_labels = "er_labels"
    module_labels = "module_labels"
    testcase_labels = "testcase_labels"


class UnitStatus(str, Enum):
    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"
    skipped = "skipped"


@dataclass
class FrozenSpec:
    """Plan 确认后不可被 LLM 单元改动的字段（对标 outline confirmed 后冻结页序）。"""

    domain: str = ""
    title: str = ""
    accept: str = ""
    scene: str = ""
    persistence: str = "jdbc"
    spring_security: bool = False
    capabilities: list[str] = field(default_factory=list)
    archetypes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TaskUnit:
    id: str
    kind: UnitKind
    payload: dict[str, Any]
    status: UnitStatus = UnitStatus.pending
    source_refs: list[str] = field(default_factory=list)
    budget_chars: int = 2000
    attempts: int = 0
    max_attempts: int = 2
    error: str = ""
    tokens: int = 0
    patch: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["kind"] = self.kind.value
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskUnit:
        return cls(
            id=str(data["id"]),
            kind=UnitKind(str(data["kind"])),
            payload=dict(data.get("payload") or {}),
            status=UnitStatus(str(data.get("status") or UnitStatus.pending.value)),
            source_refs=list(data.get("source_refs") or []),
            budget_chars=int(data.get("budget_chars") or 2000),
            attempts=int(data.get("attempts") or 0),
            max_attempts=int(data.get("max_attempts") or 2),
            error=str(data.get("error") or ""),
            tokens=int(data.get("tokens") or 0),
            patch=data.get("patch") if isinstance(data.get("patch"), dict) else None,
        )


@dataclass
class DeliveryPlan:
    version: int = 1
    frozen: FrozenSpec = field(default_factory=FrozenSpec)
    units: list[TaskUnit] = field(default_factory=list)
    proposal_excerpt: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "frozen": self.frozen.to_dict(),
            "units": [u.to_dict() for u in self.units],
            "proposal_excerpt": self.proposal_excerpt,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeliveryPlan:
        frozen_raw = data.get("frozen") or {}
        return cls(
            version=int(data.get("version") or 1),
            frozen=FrozenSpec(**{k: frozen_raw.get(k) for k in FrozenSpec.__dataclass_fields__}),
            units=[TaskUnit.from_dict(u) for u in (data.get("units") or [])],
            proposal_excerpt=str(data.get("proposal_excerpt") or ""),
        )


@dataclass
class UnitResult:
    unit_id: str
    status: UnitStatus
    patch: dict[str, Any] | None = None
    tokens: int = 0
    error: str = ""
    attempts: int = 0
    context: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "status": self.status.value,
            "patch": self.patch,
            "tokens": self.tokens,
            "error": self.error,
            "attempts": self.attempts,
            "context": self.context,
        }


@dataclass
class FlowRunSummary:
    plan: DeliveryPlan
    results: list[UnitResult] = field(default_factory=list)
    merged: bool = False
    merge_detail: str = ""
    merge_result: FillMergeResult | None = None

    @property
    def done(self) -> int:
        return sum(1 for r in self.results if r.status == UnitStatus.done)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == UnitStatus.failed)

    @property
    def skipped(self) -> int:
        return sum(1 for r in self.results if r.status == UnitStatus.skipped)

    def to_dict(self) -> dict[str, Any]:
        return {
            "done": self.done,
            "failed": self.failed,
            "skipped": self.skipped,
            "total": len(self.results),
            "merged": self.merged,
            "merge_detail": self.merge_detail,
            "merge_result": {
                "ok": self.merge_result.ok,
                "mode": self.merge_result.mode,
                "er_filled": self.merge_result.er_filled,
                "module_filled": self.merge_result.module_filled,
                "testcase_filled": self.merge_result.testcase_filled,
                "written": self.merge_result.written,
            }
            if self.merge_result
            else None,
            "results": [r.to_dict() for r in self.results],
        }
