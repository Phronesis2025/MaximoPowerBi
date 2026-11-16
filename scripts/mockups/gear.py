"""Gear-and-wrench status mark as plain polygons and circles."""
import math
def gear_wrench(cx, cy, size, color, bg):
    out = []
    R = size / 2.0
    r_tip, r_body, r_hole = R, 0.78 * R, 0.40 * R
    for i in range(8):
        a, half = math.radians(i * 45.0), math.radians(17.0)
        pts = [f"{cx + rr * math.cos(aa):.1f},{cy + rr * math.sin(aa):.1f}"
               for rr, aa in ((r_body * .96, a - half), (r_tip, a - half * .68),
                              (r_tip, a + half * .68), (r_body * .96, a + half))]
        out.append(f'<polygon points="{" ".join(pts)}" fill="{color}"/>')
    out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{(r_body + r_hole) / 2:.1f}" fill="none" '
               f'stroke="{color}" stroke-width="{r_body - r_hole:.1f}"/>')
    ux = uy = math.cos(math.radians(45)); px, py = -uy, ux
    L = 1.15 * R
    ax, ay, bx, by = cx - ux * L, cy - uy * L, cx + ux * L, cy + uy * L
    hw, rj = .15 * R, .30 * R
    def bar(h, r, fill):
        c = [f"{ax + px * h:.1f},{ay + py * h:.1f}", f"{bx + px * h:.1f},{by + py * h:.1f}",
             f"{bx - px * h:.1f},{by - py * h:.1f}", f"{ax - px * h:.1f},{ay - py * h:.1f}"]
        return [f'<polygon points="{" ".join(c)}" fill="{fill}"/>',
                f'<circle cx="{ax:.1f}" cy="{ay:.1f}" r="{r:.1f}" fill="{fill}"/>',
                f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="{r:.1f}" fill="{fill}"/>']
    def notch(ex, ey, sx, sy):
        v = [(ex + sx * rj * 1.7 + px * rj * .52, ey + sy * rj * 1.7 + py * rj * .52),
             (ex + sx * rj * 1.7 - px * rj * .52, ey + sy * rj * 1.7 - py * rj * .52),
             (ex + sx * rj * .02, ey + sy * rj * .02)]
        return f'<polygon points="{" ".join(f"{a:.1f},{b:.1f}" for a, b in v)}" fill="{bg}"/>'
    out += bar(hw + size * .055, rj + size * .055, bg) + bar(hw, rj, color)
    out += [notch(ax, ay, -ux, -uy), notch(bx, by, ux, uy)]
    return out
