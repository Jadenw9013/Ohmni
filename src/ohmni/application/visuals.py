"""Deterministic SVG views derived from exact semantic and physical artifacts."""

from __future__ import annotations

from html import escape


def schematic_svg(circuit, artifact) -> str:
    components=sorted(circuit.components,key=lambda item:item.ref)
    width=900;height=max(360,110+len(components)*38)
    lines=[f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Compiled schematic topology">','<rect width="100%" height="100%" fill="#0b1110"/>',f'<text x="28" y="34" fill="#dce9df" font-size="16">Compiled artifact {escape(artifact.fingerprint.digest[:12])}</text>']
    nets={net.name:index for index,net in enumerate(sorted(circuit.nets,key=lambda item:item.name))}
    for name,index in nets.items():
        x=590+(index%3)*95;y=72+(index//3)*34
        lines.append(f'<circle cx="{x}" cy="{y}" r="4" fill="#d6a84b"/><text x="{x+9}" y="{y+4}" fill="#91a49a" font-size="10">{escape(name)}</text>')
    for index,component in enumerate(components):
        x=35+(index%2)*250;y=70+(index//2)*70
        lines.append(f'<rect x="{x}" y="{y}" width="190" height="46" rx="4" fill="#15211e" stroke="#41665a"/><text x="{x+12}" y="{y+20}" fill="#f2f7f4" font-size="13">{escape(component.ref)} · {escape(component.part_id)}</text><text x="{x+12}" y="{y+36}" fill="#91a49a" font-size="10">{escape(component.package)}</text>')
    lines.append('</svg>');return ''.join(lines)


def pcb_svg(board, plan) -> str:
    scale=7;pad=24;width=board.outline.width_mm*scale+pad*2;height=board.outline.height_mm*scale+pad*2
    lines=[f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Exact routed PCB geometry">','<rect width="100%" height="100%" fill="#08100e"/>',f'<rect x="{pad}" y="{pad}" width="{board.outline.width_mm*scale}" height="{board.outline.height_mm*scale}" rx="8" fill="#12372d" stroke="#62b592" stroke-width="2"/>']
    for track in plan.tracks:
        color="#f1bd55" if track.layer=="F.Cu" else "#65a9d8"
        lines.append(f'<line x1="{pad+track.start.x_mm*scale:.2f}" y1="{pad+track.start.y_mm*scale:.2f}" x2="{pad+track.end.x_mm*scale:.2f}" y2="{pad+track.end.y_mm*scale:.2f}" stroke="{color}" stroke-width="{max(1.2,track.width_mm*scale):.2f}" stroke-linecap="round"><title>{escape(track.net_name)} · {track.layer}</title></line>')
    for via in plan.vias:
        lines.append(f'<circle cx="{pad+via.position.x_mm*scale:.2f}" cy="{pad+via.position.y_mm*scale:.2f}" r="3.2" fill="#0b1110" stroke="#e8d7a7"><title>{escape(via.net_name)} via</title></circle>')
    for placement in board.placements:
        x=pad+placement.x_mm*scale;y=pad+placement.y_mm*scale
        lines.append(f'<rect x="{x-12}" y="{y-8}" width="24" height="16" rx="2" fill="#d9e5de" fill-opacity=".9"/><text x="{x}" y="{y+3}" text-anchor="middle" font-size="7" fill="#07100d">{escape(placement.component_ref)}</text><title>{escape(placement.reason)}</title>')
    lines.append('</svg>');return ''.join(lines)

