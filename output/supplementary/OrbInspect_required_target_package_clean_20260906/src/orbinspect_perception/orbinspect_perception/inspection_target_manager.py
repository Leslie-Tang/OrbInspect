"""Generate inspection targets on the simplified OrbInspect station proxy."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import count


Vector3 = tuple[float, float, float]


@dataclass(frozen=True)
class InspectionTarget:
    """A target point and outward surface normal on the station proxy."""

    target_id: str
    position: Vector3
    normal: Vector3


class InspectionTargetManager:
    """Generate target points on the ISS proxy primitives."""

    def __init__(self, spacing: float = 8.0) -> None:
        if spacing <= 0.0:
            raise ValueError('spacing must be positive')
        self.spacing = float(spacing)

    def generate_targets(self) -> list[InspectionTarget]:
        """Return deterministic targets on truss, arrays, modules, and node."""
        target_counter = count()
        targets: list[InspectionTarget] = []
        boxes = (
            ('main_truss', (0.0, 0.0, 0.0), (80.0, 4.0, 4.0)),
            ('left_array', (-25.0, 0.0, 12.0), (30.0, 1.0, 12.0)),
            ('right_array', (25.0, 0.0, 12.0), (30.0, 1.0, 12.0)),
        )
        cylinders = (
            ('module_1', (0.0, 8.0, 0.0), 3.0, 15.0, 'x'),
            ('module_2', (0.0, -8.0, 0.0), 3.0, 15.0, 'x'),
            ('docking_node', (0.0, 0.0, -6.0), 2.0, 6.0, 'z'),
        )
        for name, center, size in boxes:
            targets.extend(self._box_targets(name, center, size, target_counter))
        for name, center, radius, length, axis in cylinders:
            targets.extend(
                self._cylinder_targets(name, center, radius, length, axis, target_counter)
            )
        return targets

    def _box_targets(
        self,
        prefix: str,
        center: Vector3,
        size: Vector3,
        target_counter: count,
    ) -> list[InspectionTarget]:
        cx, cy, cz = center
        sx, sy, sz = size
        faces = [
            ((cx + sx / 2.0, cy, cz), (1.0, 0.0, 0.0), (1, 2), (sy, sz)),
            ((cx - sx / 2.0, cy, cz), (-1.0, 0.0, 0.0), (1, 2), (sy, sz)),
            ((cx, cy + sy / 2.0, cz), (0.0, 1.0, 0.0), (0, 2), (sx, sz)),
            ((cx, cy - sy / 2.0, cz), (0.0, -1.0, 0.0), (0, 2), (sx, sz)),
            ((cx, cy, cz + sz / 2.0), (0.0, 0.0, 1.0), (0, 1), (sx, sy)),
            ((cx, cy, cz - sz / 2.0), (0.0, 0.0, -1.0), (0, 1), (sx, sy)),
        ]
        targets: list[InspectionTarget] = []
        for face_center, normal, axes, extents in faces:
            for offset_a in self._sample_offsets(extents[0]):
                for offset_b in self._sample_offsets(extents[1]):
                    position = [face_center[0], face_center[1], face_center[2]]
                    position[axes[0]] += offset_a
                    position[axes[1]] += offset_b
                    targets.append(
                        self._make_target(prefix, tuple(position), normal, target_counter)
                    )
        return targets

    def _cylinder_targets(
        self,
        prefix: str,
        center: Vector3,
        radius: float,
        length: float,
        axis: str,
        target_counter: count,
    ) -> list[InspectionTarget]:
        import math

        targets: list[InspectionTarget] = []
        angle_count = max(8, int(round(2.0 * math.pi * radius / self.spacing)))
        axial_offsets = self._sample_offsets(length)
        for axial_offset in axial_offsets:
            for index in range(angle_count):
                angle = 2.0 * math.pi * index / angle_count
                radial_a = radius * math.cos(angle)
                radial_b = radius * math.sin(angle)
                if axis == 'x':
                    position = (
                        center[0] + axial_offset,
                        center[1] + radial_a,
                        center[2] + radial_b,
                    )
                    normal = (0.0, math.cos(angle), math.sin(angle))
                elif axis == 'z':
                    position = (
                        center[0] + radial_a,
                        center[1] + radial_b,
                        center[2] + axial_offset,
                    )
                    normal = (math.cos(angle), math.sin(angle), 0.0)
                else:
                    raise ValueError('axis must be x or z')
                targets.append(self._make_target(prefix, position, normal, target_counter))
        return targets

    def _sample_offsets(self, extent: float) -> list[float]:
        sample_count = max(1, int(extent // self.spacing) + 1)
        if sample_count == 1:
            return [0.0]
        start = -extent / 2.0
        step = extent / float(sample_count - 1)
        return [start + step * index for index in range(sample_count)]

    @staticmethod
    def _make_target(
        prefix: str,
        position: Vector3,
        normal: Vector3,
        target_counter: count,
    ) -> InspectionTarget:
        return InspectionTarget(
            target_id=f'{prefix}_{next(target_counter):04d}',
            position=tuple(float(value) for value in position),
            normal=tuple(float(value) for value in normal),
        )
