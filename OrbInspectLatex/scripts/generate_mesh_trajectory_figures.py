"""Generate mesh-overlaid trajectory figures for the OrbInspect manuscript."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
import struct

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Line3DCollection
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / 'data' / 'offline_high_coverage_experiment' / 'raw'
MESH_PATH = ROOT / 'data' / 'iss_mesh' / 'ISS_stationary.glb'
FIGURE_DIR = ROOT / 'figures' / 'high_coverage'
MESH_SCALE = 1.065
MESH_EDGE_BUDGET = 60000
MESH_FACE_BUDGET = 18000


def main() -> None:
    """Regenerate trajectory figures from archived CSVs and the copied ISS GLB."""
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    trajectories = load_trajectories(DATA_DIR / 'trajectory.csv')
    viewpoints = load_viewpoints(DATA_DIR / 'viewpoints.csv')
    mesh_segments = load_mesh_segments(MESH_PATH, scale=MESH_SCALE, max_edges=MESH_EDGE_BUDGET)
    mesh_faces = load_mesh_faces(MESH_PATH, scale=MESH_SCALE, max_faces=MESH_FACE_BUDGET)

    plot_proposed_trajectory(
        FIGURE_DIR / 'proposed_trajectory_3d.png',
        mesh_segments,
        mesh_faces,
        trajectories['set_cover_cw_tour'],
        viewpoints['set_cover_cw_tour'],
    )
    plot_method_comparison(
        FIGURE_DIR / 'trajectory_method_comparison.png',
        mesh_segments,
        mesh_faces,
        trajectories,
    )


def load_trajectories(path: Path) -> dict[str, list[tuple[float, float, float]]]:
    """Load method-indexed LVLH trajectory samples."""
    by_method: dict[str, list[tuple[float, float, float]]] = {}
    with path.open(newline='') as handle:
        for row in csv.DictReader(handle):
            by_method.setdefault(row['method'], []).append((
                float(row['rx']),
                float(row['ry']),
                float(row['rz']),
            ))
    return by_method


def load_viewpoints(path: Path) -> dict[str, list[dict[str, float]]]:
    """Load selected viewpoint positions and coverage values."""
    by_method: dict[str, list[dict[str, float]]] = {}
    with path.open(newline='') as handle:
        for row in csv.DictReader(handle):
            by_method.setdefault(row['method'], []).append({
                'sequence': float(row['sequence']),
                'x': float(row['viewpoint_x']),
                'y': float(row['viewpoint_y']),
                'z': float(row['viewpoint_z']),
                'coverage': float(row['cumulative_coverage']),
            })
    return by_method


def plot_proposed_trajectory(
    path: Path,
    mesh_segments: list[tuple[tuple[float, float, float], tuple[float, float, float]]],
    mesh_faces: list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]],
    trajectory: list[tuple[float, float, float]],
    viewpoints: list[dict[str, float]],
) -> None:
    """Plot the proposed trajectory in the same frame as the ISS mesh."""
    fig = plt.figure(figsize=(7.4, 5.8))
    ax = fig.add_subplot(111, projection='3d')
    draw_mesh(ax, mesh_segments, mesh_faces)

    xs, ys, zs = unzip_points(trajectory)
    ax.plot(xs, ys, zs, color='#005DAA', linewidth=3.7, label='set-cover CW tour', zorder=8)
    ax.scatter([xs[0]], [ys[0]], [zs[0]], s=70, c='#00876C', marker='o', label='start', depthshade=False)
    ax.scatter([xs[-1]], [ys[-1]], [zs[-1]], s=85, c='#D55E00', marker='X', label='end', depthshade=False)

    if viewpoints:
        scatter = ax.scatter(
            [item['x'] for item in viewpoints],
            [item['y'] for item in viewpoints],
            [item['z'] for item in viewpoints],
            c=[item['coverage'] for item in viewpoints],
            cmap='viridis',
            s=54,
            marker='^',
            edgecolors='black',
            linewidths=0.25,
            depthshade=False,
            label='selected viewpoints',
            zorder=9,
        )
        colorbar = fig.colorbar(scatter, ax=ax, shrink=0.62, pad=0.07)
        colorbar.set_label('cumulative coverage')

    style_axis(ax)
    set_equal_axes(ax, mesh_segments, trajectory)
    ax.legend(loc='upper left', frameon=True, framealpha=0.9)
    save_all(fig, path)


def plot_method_comparison(
    path: Path,
    mesh_segments: list[tuple[tuple[float, float, float], tuple[float, float, float]]],
    mesh_faces: list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]],
    trajectories: dict[str, list[tuple[float, float, float]]],
) -> None:
    """Plot all method trajectories against the same ISS mesh."""
    labels = {
        'set_cover_cw_tour': 'Set-cover CW tour',
        'proposed_safe_cw_nbv': 'Safe CW NBV',
        'coverage_greedy': 'Coverage greedy',
        'safe_coverage_greedy': 'Safe coverage greedy',
        'distance_greedy': 'Nearest NBV',
        'fuel_greedy': 'Fuel greedy',
        'random_safe': 'Random safe',
    }
    colors = {
        'set_cover_cw_tour': '#005DAA',
        'proposed_safe_cw_nbv': '#7A5195',
        'coverage_greedy': '#EF5675',
        'safe_coverage_greedy': '#FFA600',
        'distance_greedy': '#2ca25f',
        'fuel_greedy': '#4C78A8',
        'random_safe': '#7F7F7F',
    }

    fig = plt.figure(figsize=(7.4, 5.8))
    ax = fig.add_subplot(111, projection='3d')
    draw_mesh(ax, mesh_segments, mesh_faces)
    all_points: list[tuple[float, float, float]] = []

    for method, trajectory in trajectories.items():
        if not trajectory:
            continue
        xs, ys, zs = unzip_points(trajectory)
        is_proposed = method == 'set_cover_cw_tour'
        ax.plot(
            xs,
            ys,
            zs,
            color=colors.get(method, '#333333'),
            linewidth=3.8 if is_proposed else 2.0,
            alpha=1.0 if is_proposed else 0.68,
            label=labels.get(method, method),
            zorder=9 if is_proposed else 7,
        )
        all_points.extend(trajectory)

    style_axis(ax)
    set_equal_axes(ax, mesh_segments, all_points)
    ax.legend(loc='upper left', frameon=True, framealpha=0.9, ncol=1)
    save_all(fig, path)


def draw_mesh(
    ax,
    segments: list[tuple[tuple[float, float, float], tuple[float, float, float]]],
    faces: list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]],
) -> None:
    """Draw the ISS mesh as a dense wireframe with a subtle surface layer."""
    if faces:
        surface = Poly3DCollection(
            faces,
            facecolors='#BFC5CC',
            edgecolors='none',
            alpha=0.10,
            zorder=0,
        )
        ax.add_collection3d(surface)
    collection = Line3DCollection(
        segments,
        colors='#4A4A4A',
        linewidths=0.16,
        alpha=0.34,
        zorder=1,
    )
    ax.add_collection3d(collection)
    ax.plot([], [], [], color='#4A4A4A', linewidth=1.2, alpha=0.70, label='ISS mesh')


def style_axis(ax) -> None:
    """Apply journal-friendly 3D axis styling."""
    ax.set_xlabel('Radial x (m)', labelpad=8)
    ax.set_ylabel('Along-track y (m)', labelpad=8)
    ax.set_zlabel('Cross-track z (m)', labelpad=8)
    ax.view_init(elev=20.0, azim=-54.0)
    ax.grid(True, color='#D9D9D9', linewidth=0.55)
    for pane in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
        pane.set_facecolor((1.0, 1.0, 1.0, 0.0))
        pane.set_edgecolor('#E6E6E6')


def set_equal_axes(
    ax,
    mesh_segments: list[tuple[tuple[float, float, float], tuple[float, float, float]]],
    points: list[tuple[float, float, float]],
) -> None:
    """Use one equal-scale 3D box containing both mesh and trajectories."""
    all_points = list(points)
    for first, second in mesh_segments:
        all_points.extend((first, second))
    xs, ys, zs = unzip_points(all_points)
    center = (
        (min(xs) + max(xs)) / 2.0,
        (min(ys) + max(ys)) / 2.0,
        (min(zs) + max(zs)) / 2.0,
    )
    radius = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)) * 0.54
    ax.set_xlim(center[0] - radius, center[0] + radius)
    ax.set_ylim(center[1] - radius, center[1] + radius)
    ax.set_zlim(center[2] - radius, center[2] + radius)


def save_all(fig, path: Path) -> None:
    """Save PNG, PDF, and SVG versions of a figure."""
    fig.tight_layout()
    for suffix in ('.png', '.pdf', '.svg'):
        fig.savefig(path.with_suffix(suffix), dpi=360, bbox_inches='tight')
    plt.close(fig)


def unzip_points(points: list[tuple[float, float, float]]) -> tuple[list[float], list[float], list[float]]:
    """Split a list of 3D points into x, y, and z coordinate lists."""
    return (
        [point[0] for point in points],
        [point[1] for point in points],
        [point[2] for point in points],
    )


def load_mesh_segments(
    path: Path,
    scale: float,
    max_edges: int,
) -> list[tuple[tuple[float, float, float], tuple[float, float, float]]]:
    """Load a downsampled GLB wireframe in the planner's LVLH convention."""
    json_doc, binary = read_glb(path)
    nodes = json_doc.get('nodes', [])
    meshes = json_doc.get('meshes', [])
    if not isinstance(nodes, list) or not isinstance(meshes, list):
        return []

    transforms = node_translations(json_doc)
    primitive_count = sum(
        len(mesh.get('primitives', []))
        for mesh in meshes
        if isinstance(mesh, dict)
    )
    edge_budget = max(1, max_edges // max(1, primitive_count))
    segments: list[tuple[tuple[float, float, float], tuple[float, float, float]]] = []

    for node in nodes:
        if not isinstance(node, dict) or 'mesh' not in node:
            continue
        mesh_index = int(node['mesh'])
        if mesh_index >= len(meshes) or not isinstance(meshes[mesh_index], dict):
            continue
        translation = transforms.get(id(node), (0.0, 0.0, 0.0))
        for primitive in meshes[mesh_index].get('primitives', []):
            if not isinstance(primitive, dict) or primitive.get('mode', 4) != 4:
                continue
            attributes = primitive.get('attributes', {})
            if not isinstance(attributes, dict) or 'POSITION' not in attributes:
                continue
            positions = read_accessor_vec3(json_doc, binary, int(attributes['POSITION']))
            indices = read_accessor_indices(json_doc, binary, primitive.get('indices'))
            triangle_count = len(indices) // 3 if indices else len(positions) // 3
            stride = max(1, math.ceil((triangle_count * 3) / edge_budget))
            for start in range(0, triangle_count * 3, 3 * stride):
                if indices:
                    tri = indices[start:start + 3]
                    if len(tri) < 3 or max(tri) >= len(positions):
                        continue
                    raw_points = [positions[index] for index in tri]
                else:
                    raw_points = positions[start:start + 3]
                    if len(raw_points) < 3:
                        continue
                vertices = [transform_iss_vertex(point, translation, scale) for point in raw_points]
                segments.extend(((vertices[0], vertices[1]), (vertices[1], vertices[2]), (vertices[2], vertices[0])))
                if len(segments) >= max_edges:
                    return segments
    return segments


def load_mesh_faces(
    path: Path,
    scale: float,
    max_faces: int,
) -> list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]]:
    """Load a downsampled GLB triangle surface in the planner's LVLH convention."""
    json_doc, binary = read_glb(path)
    nodes = json_doc.get('nodes', [])
    meshes = json_doc.get('meshes', [])
    if not isinstance(nodes, list) or not isinstance(meshes, list) or max_faces <= 0:
        return []

    transforms = node_translations(json_doc)
    primitive_count = sum(
        len(mesh.get('primitives', []))
        for mesh in meshes
        if isinstance(mesh, dict)
    )
    face_budget = max(1, max_faces // max(1, primitive_count))
    faces: list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]] = []

    for node in nodes:
        if not isinstance(node, dict) or 'mesh' not in node:
            continue
        mesh_index = int(node['mesh'])
        if mesh_index >= len(meshes) or not isinstance(meshes[mesh_index], dict):
            continue
        translation = transforms.get(id(node), (0.0, 0.0, 0.0))
        for primitive in meshes[mesh_index].get('primitives', []):
            if not isinstance(primitive, dict) or primitive.get('mode', 4) != 4:
                continue
            attributes = primitive.get('attributes', {})
            if not isinstance(attributes, dict) or 'POSITION' not in attributes:
                continue
            positions = read_accessor_vec3(json_doc, binary, int(attributes['POSITION']))
            indices = read_accessor_indices(json_doc, binary, primitive.get('indices'))
            triangle_count = len(indices) // 3 if indices else len(positions) // 3
            stride = max(1, math.ceil(triangle_count / face_budget))
            for triangle_index in range(0, triangle_count, stride):
                start = triangle_index * 3
                if indices:
                    tri = indices[start:start + 3]
                    if len(tri) < 3 or max(tri) >= len(positions):
                        continue
                    raw_points = [positions[index] for index in tri]
                else:
                    raw_points = positions[start:start + 3]
                    if len(raw_points) < 3:
                        continue
                vertices = tuple(
                    transform_iss_vertex(point, translation, scale)
                    for point in raw_points
                )
                faces.append(vertices)
                if len(faces) >= max_faces:
                    return faces
    return faces


def read_glb(path: Path) -> tuple[dict[str, object], bytes]:
    """Read a binary glTF 2.0 file."""
    with path.open('rb') as handle:
        magic, version, _length = struct.unpack('<4sII', handle.read(12))
        if magic != b'glTF' or version != 2:
            raise ValueError(f'expected GLB v2 file: {path}')
        json_length, json_type = struct.unpack('<I4s', handle.read(8))
        if json_type != b'JSON':
            raise ValueError('first GLB chunk must be JSON')
        json_doc = json.loads(handle.read(json_length).decode('utf-8'))
        binary = b''
        while True:
            header = handle.read(8)
            if not header:
                break
            chunk_length, chunk_type = struct.unpack('<I4s', header)
            chunk_data = handle.read(chunk_length)
            if chunk_type == b'BIN\x00':
                binary = chunk_data
                break
    if not binary:
        raise ValueError('GLB does not contain a binary buffer')
    return json_doc, binary


def node_translations(json_doc: dict[str, object]) -> dict[int, tuple[float, float, float]]:
    """Return accumulated node translations keyed by object identity."""
    nodes = json_doc.get('nodes', [])
    if not isinstance(nodes, list):
        return {}
    scene_index = int(json_doc.get('scene', 0))
    scenes = json_doc.get('scenes', [])
    if isinstance(scenes, list) and scene_index < len(scenes) and isinstance(scenes[scene_index], dict):
        roots = [int(item) for item in scenes[scene_index].get('nodes', [])]
    else:
        roots = list(range(len(nodes)))

    transforms: dict[int, tuple[float, float, float]] = {}

    def visit(node_index: int, parent: tuple[float, float, float]) -> None:
        if node_index >= len(nodes) or not isinstance(nodes[node_index], dict):
            return
        node = nodes[node_index]
        local = vector3(node.get('translation', (0.0, 0.0, 0.0)))
        translation = (parent[0] + local[0], parent[1] + local[1], parent[2] + local[2])
        transforms[id(node)] = translation
        for child in node.get('children', []):
            visit(int(child), translation)

    for root in roots:
        visit(root, (0.0, 0.0, 0.0))
    return transforms


def read_accessor_vec3(
    json_doc: dict[str, object],
    binary: bytes,
    accessor_index: int,
) -> list[tuple[float, float, float]]:
    """Read a float VEC3 accessor."""
    accessor, offset, stride = accessor_buffer(json_doc, accessor_index)
    if accessor.get('componentType') != 5126 or accessor.get('type') != 'VEC3':
        return []
    return [
        struct.unpack_from('<fff', binary, offset + index * stride)
        for index in range(int(accessor.get('count', 0)))
    ]


def read_accessor_indices(json_doc: dict[str, object], binary: bytes, accessor_index: object) -> list[int]:
    """Read unsigned triangle indices from a glTF accessor."""
    if accessor_index is None:
        return []
    accessor, offset, stride = accessor_buffer(json_doc, int(accessor_index))
    component_type = int(accessor.get('componentType', 0))
    if component_type == 5123:
        fmt, default_stride = '<H', 2
    elif component_type == 5125:
        fmt, default_stride = '<I', 4
    else:
        return []
    stride = max(stride, default_stride)
    return [
        int(struct.unpack_from(fmt, binary, offset + index * stride)[0])
        for index in range(int(accessor.get('count', 0)))
    ]


def accessor_buffer(
    json_doc: dict[str, object],
    accessor_index: int,
) -> tuple[dict[str, object], int, int]:
    """Return accessor metadata, byte offset, and byte stride."""
    accessors = json_doc['accessors']
    buffer_views = json_doc['bufferViews']
    accessor = accessors[accessor_index]
    buffer_view = buffer_views[int(accessor['bufferView'])]
    offset = int(buffer_view.get('byteOffset', 0)) + int(accessor.get('byteOffset', 0))
    stride = int(buffer_view.get('byteStride', 0))
    if stride <= 0:
        component_size = 2 if int(accessor.get('componentType', 5126)) == 5123 else 4
        component_count = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3}.get(accessor.get('type', 'SCALAR'), 1)
        stride = component_size * component_count
    return accessor, offset, stride


def transform_iss_vertex(
    point: tuple[float, float, float],
    translation: tuple[float, float, float],
    scale: float,
) -> tuple[float, float, float]:
    """Match the planner and SDF ISS visual pose in LVLH coordinates."""
    translated = (
        point[0] + translation[0],
        point[1] + translation[1],
        point[2] + translation[2],
    )
    return (
        scale * translated[2],
        scale * translated[1],
        -scale * translated[0],
    )


def vector3(values: object) -> tuple[float, float, float]:
    """Convert a glTF translation field into a 3-vector."""
    if not isinstance(values, (list, tuple)) or len(values) != 3:
        return (0.0, 0.0, 0.0)
    return (float(values[0]), float(values[1]), float(values[2]))


if __name__ == '__main__':
    plt.switch_backend('Agg')
    plt.rcParams.update({
        'font.family': 'DejaVu Sans',
        'font.size': 9,
        'axes.labelsize': 9,
        'legend.fontsize': 8,
        'xtick.labelsize': 8,
        'ytick.labelsize': 8,
        'figure.dpi': 180,
        'savefig.dpi': 360,
        'pdf.fonttype': 42,
        'ps.fonttype': 42,
    })
    main()
