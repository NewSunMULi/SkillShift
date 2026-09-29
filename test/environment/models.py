"""环境数据模型与标签提取。 / Environment models and tag extraction."""

from __future__ import annotations

from dataclasses import dataclass


def environment_tags(name: str) -> frozenset[str]:
    """生成可复用的环境语义标签。 / Build reusable semantic tags for an environment."""
    tags = {name}
    groups = {
        "cold": {"light_snow", "heavy_snow", "extreme_cold", "ice"},
        "radiation": {"radiation", "high_radiation"},
        "obscured": {"dust", "dust_storm", "low_visibility"},
        "rough": {"steep_slope", "dense_rocks", "sharp_rocks", "crater", "rough_terrain"},
        "bright": {"sunny", "clear"},
    }
    tags.update(tag for tag, members in groups.items() if name in members)
    return frozenset(tags)


@dataclass(frozen=True)
class Environment:
    """描述外部环境，不包含探测器内部状态。 / External conditions without rover state."""

    name: str
    tags: frozenset[str]

    @classmethod
    def from_name(cls, name: str) -> "Environment":
        return cls(name=name, tags=environment_tags(name))
