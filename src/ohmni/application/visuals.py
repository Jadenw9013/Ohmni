"""Deterministic SVG views derived from exact semantic and physical artifacts."""

from __future__ import annotations

from html import escape


def schematic_svg(artifact) -> str:
    """Render the compiler-owned KiCad sheet geometry and global-label topology."""
    if artifact.compilation.source_artifact_fingerprint != artifact.fingerprint:
        raise ValueError("schematic projection fingerprint does not match artifact")
    if artifact.compilation.connection_method != "global_labels":
        raise ValueError("unsupported schematic connection projection")
    bindings = sorted(artifact.compilation.symbol_bindings, key=lambda item: item.component_ref)
    scale = 4.2
    pad = 24
    max_x = max((binding.x_mm + binding.width_mm for binding in bindings), default=100)
    max_y = max((binding.y_mm + 1.27 for binding in bindings), default=80)
    width = max(720, max_x * scale + pad * 2)
    height = max(420, max_y * scale + pad * 2)
    lines = [
        (f'<svg viewBox="0 0 {width:.2f} {height:.2f}" role="img" '
         f'aria-label="Compiled schematic sheet geometry" '
         f'data-source-fingerprint="{escape(artifact.fingerprint.digest)}">'),
        '<rect width="100%" height="100%" fill="#0b1110"/>',
        (f'<text x="{pad}" y="20" fill="#dce9df" font-size="12">'
         f'Compiled KiCad artifact {escape(artifact.fingerprint.digest[:12])} · '
        'matching global labels are electrically connected</text>'),
    ]
    represented_nets: set[str] = set()
    for driver in artifact.compilation.driver_bindings:
        driver_x = pad + driver.x_mm * scale
        driver_y = pad + driver.y_mm * scale
        represented_nets.add(driver.net_name)
        lines.append(
            f'<g data-compiler-driver="{escape(driver.reference)}" '
            f'data-role="{escape(driver.role)}" data-net="{escape(driver.net_name)}" '
            f'data-symbol-uuid="{escape(driver.symbol_uuid)}" '
            f'data-endpoint-uuid="{escape(driver.endpoint_uuid)}">'
            f'<rect x="{driver_x - 4:.2f}" y="{driver_y - 4:.2f}" width="8" height="8" '
            f'transform="rotate(45 {driver_x:.2f} {driver_y:.2f})" fill="#d6a84b"/>'
            f'<text x="{driver_x + 7:.2f}" y="{driver_y + 3:.2f}" fill="#dce9df" font-size="8">'
            f'{escape(driver.reference)} · {escape(driver.net_name)}</text></g>'
        )
    for binding in bindings:
        x = pad + (binding.x_mm - binding.width_mm / 2) * scale
        y = pad + (binding.y_mm - (binding.height_mm - 1.27)) * scale
        lines.append(
            f'<g data-component-ref="{escape(binding.component_ref)}" '
            f'data-symbol-uuid="{escape(binding.symbol_uuid)}">'
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{binding.width_mm * scale:.2f}" '
            f'height="{binding.height_mm * scale:.2f}" rx="3" fill="#15211e" stroke="#41665a"/>'
            f'<text x="{x + 5:.2f}" y="{y + 15:.2f}" fill="#f2f7f4" font-size="11">'
            f'{escape(binding.component_ref)} · {escape(binding.part_id)}</text></g>'
        )
        for pin in binding.pins:
            pin_x = pad + pin.x_mm * scale
            pin_y = pad + pin.y_mm * scale
            net_name = pin.net_name or "NO_CONNECT"
            if pin.net_name:
                represented_nets.add(pin.net_name)
            lines.append(
                f'<g data-pin="{escape(pin.component_ref)}.{escape(pin.circuit_pin)}" '
                f'data-net="{escape(net_name)}" data-pin-uuid="{escape(pin.pin_uuid)}" '
                f'data-endpoint-uuid="{escape(pin.endpoint_uuid)}" '
                f'data-angle="{pin.angle_degrees}">'
                f'<circle cx="{pin_x:.2f}" cy="{pin_y:.2f}" r="2.2" '
                f'fill="{("#d6a84b" if pin.net_name else "#66756e")}"/>'
                f'<text x="{pin_x + 4:.2f}" y="{pin_y + 3:.2f}" fill="#91a49a" font-size="7">'
                f'{escape(net_name)}</text></g>'
            )
    missing_nets = set(artifact.compilation.net_mapping) - represented_nets
    if missing_nets:
        raise ValueError(f"compiled schematic geometry omits nets: {sorted(missing_nets)}")
    lines.append("</svg>")
    return "".join(lines)


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
