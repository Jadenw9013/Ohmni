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


def pcb_svg(board, artifact) -> str:
    """Render only the compiler-owned copper projection for this PCB artifact."""
    compilation=artifact.compilation
    if compilation.artifact_fingerprint != artifact.fingerprint:
        raise ValueError("PCB projection fingerprint does not match artifact")
    if compilation.constraints_hash != artifact.constraints_hash or board.content_hash != artifact.constraints_hash:
        raise ValueError("PCB projection constraints lineage does not match artifact")
    if artifact.routing_plan_fingerprint is None or compilation.routing_plan_fingerprint != artifact.routing_plan_fingerprint:
        raise ValueError("PCB projection routing lineage does not match artifact")
    scale=7;pad=24;width=board.outline.width_mm*scale+pad*2;height=board.outline.height_mm*scale+pad*2
    lines=[f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Compiler-emitted routed PCB copper geometry" data-artifact-fingerprint="{escape(artifact.fingerprint.digest)}" data-routing-plan-fingerprint="{escape(artifact.routing_plan_fingerprint)}" data-constraints-hash="{escape(artifact.constraints_hash)}">','<rect width="100%" height="100%" fill="#08100e"/>',f'<rect x="{pad}" y="{pad}" width="{board.outline.width_mm*scale}" height="{board.outline.height_mm*scale}" rx="8" fill="#12372d" stroke="#62b592" stroke-width="2"/>']
    for track in compilation.emitted_tracks:
        color="#f1bd55" if track.layer=="F.Cu" else "#65a9d8"
        lines.append(f'<line data-track-uuid="{escape(track.emitted_uuid)}" data-source-segment-id="{escape(track.source_segment_id)}" data-net="{escape(track.net_name)}" data-net-number="{track.net_number}" data-layer="{escape(track.layer)}" x1="{pad+track.start_x_mm*scale:.6f}" y1="{pad+track.start_y_mm*scale:.6f}" x2="{pad+track.end_x_mm*scale:.6f}" y2="{pad+track.end_y_mm*scale:.6f}" stroke="{color}" stroke-width="{track.width_mm*scale:.6f}" stroke-linecap="round"><title>{escape(track.net_name)} · {escape(track.layer)}</title></line>')
    for via in compilation.emitted_vias:
        x=pad+via.x_mm*scale;y=pad+via.y_mm*scale
        lines.append(f'<g data-via-uuid="{escape(via.emitted_uuid)}" data-source-via-id="{escape(via.source_via_id)}" data-net="{escape(via.net_name)}" data-net-number="{via.net_number}" data-layers="{escape("/".join(via.layers))}"><circle cx="{x:.6f}" cy="{y:.6f}" r="{via.diameter_mm*scale/2:.6f}" fill="#e8d7a7"/><circle cx="{x:.6f}" cy="{y:.6f}" r="{via.drill_mm*scale/2:.6f}" fill="#0b1110"/><title>{escape(via.net_name)} via</title></g>')
    for placement in board.placements:
        x=pad+placement.x_mm*scale;y=pad+placement.y_mm*scale
        lines.append(f'<rect x="{x-12}" y="{y-8}" width="24" height="16" rx="2" fill="#d9e5de" fill-opacity=".9"/><text x="{x}" y="{y+3}" text-anchor="middle" font-size="7" fill="#07100d">{escape(placement.component_ref)}</text><title>{escape(placement.reason)}</title>')
    lines.append('</svg>');return ''.join(lines)
