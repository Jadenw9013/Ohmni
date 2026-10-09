// KiCad's physical authoring frame is Y-down. The common 3D viewer is Y-up.
// Reflect the complete source projection once, before model placement: doing it
// only to bodies would align contacts but reverse the board's handedness.
export function reflectControllerBoard(board) {
    const copy=structuredClone(board),height=board.height_mm;
    const negative=value=>value===0?0:-value;
    if(!Number.isFinite(height)||height<=0)throw new RangeError('Controller height is required');
    for(const part of copy.components){
        part.y_mm=height-part.y_mm;part.rotation_deg=negative(part.rotation_deg);
        for(const pad of part.pads){pad.y_mm=negative(pad.y_mm);if(pad.rotation_deg!==undefined)pad.rotation_deg=negative(pad.rotation_deg);}
    }
    for(const track of copy.tracks){track.start_y_mm=height-track.start_y_mm;track.end_y_mm=height-track.end_y_mm;}
    for(const via of copy.vias)via.y_mm=height-via.y_mm;
    for(const hole of copy.mounting_holes??[])hole.y_mm=height-hole.y_mm;
    return copy;
}

export function normalizeControllerSource(source) {
    if(source.display_projection)throw new Error('Controller source was already normalized');
    return {...source,board:reflectControllerBoard(source.board),display_projection:{
        source_frame:'KICAD_Y_DOWN',viewer_frame:'OHMNI_Y_UP',
        transform:'world Y = board height − source Y; local Y and rotations negated',
        source_artifact_fingerprint:source.board.artifact_fingerprint,
        kind:'READ_ONLY_DISPLAY_COORDINATE_TRANSFORM',
    }};
}
