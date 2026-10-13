"""Find layers of a part, in its print orientation, that start in mid-air (islands or long cantilevers)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import trimesh
from shapely.geometry import Polygon
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from duct.build import build_parts  # noqa: E402
from duct.params import load_params  # noqa: E402

LAYER = 0.4
REACH = 1.2  # mm a layer may overhang the one below before it counts as unsupported


def layer_polygons(mesh: trimesh.Trimesh, z: float):
    section = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if section is None:
        return []
    to_2d = np.eye(4)
    to_2d[2, 3] = -z
    planar, _ = section.to_planar(to_2D=to_2d)
    return [Polygon(p.exterior.coords, [i.coords for i in p.interiors]) for p in planar.polygons_full]


def main(name: str) -> int:
    params = load_params(Path(__file__).resolve().parent.parent / "configs" / "default.toml")
    item = build_parts(params)[name]
    oriented = item.oriented(params)
    verts, tris = oriented.tessellate(0.1, 0.2)
    mesh = trimesh.Trimesh([[v.X, v.Y, v.Z] for v in verts], np.array(tris), process=True)
    top = mesh.bounds[1][2]
    below = None
    z = LAYER / 2
    problems = 0
    while z < top:
        polys = layer_polygons(mesh, z)
        if below is not None:
            support = unary_union(below).buffer(REACH) if below else None
            for poly in polys:
                if poly.area < 0.5:
                    continue
                if support is None or not support.contains(poly):
                    uncovered = poly if support is None else poly.difference(support)
                    if uncovered.area > 0.5:
                        c = uncovered.centroid
                        print(f"z={z:6.1f}  unsupported {uncovered.area:7.1f} mm2 at print x={c.x:7.1f} y={c.y:7.1f}")
                        problems += 1
        below = polys
        z += LAYER
    print("done,", problems, "unsupported regions")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "shroud"))
