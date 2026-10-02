import { positive, finite, validateMetadata, LODS } from './validate.js';

export const SIDES = Object.freeze(['left','bottom','right','top']);

// Every public coordinate is TOP view. Bottom-view source drawings require this
// explicit conversion before becoming model data; never mirror the final model.
export function sourcePointToTop(point, view) {
    if (!['TOP','BOTTOM'].includes(view) || !Array.isArray(point) || point.length !== 2) throw new RangeError('Explicit source view required');
    point.forEach(v=>finite(v,'source point'));
    return [point[0] * (view === 'BOTTOM' ? -1 : 1), point[1]];
}

export function rowLetter(index, alphabet) {
    if (!Number.isInteger(index) || index < 0 || !/^[A-Z]{2,26}$/.test(alphabet)
        || new Set(alphabet).size !== alphabet.length || alphabet[0] !== 'A') throw new RangeError('Invalid row-letter parameter');
    let result='';
    for(let n=index+1;n>0;n=Math.floor((n-1)/alphabet.length)) result=alphabet[(n-1)%alphabet.length]+result;
    return result;
}

function isPopulated(row,col,p) {
    const d=p.depopulate;
    if(d.mode==='none')return true;
    if(d.mode==='center')return !(row >= (p.ny-d.ny)/2 && row < (p.ny+d.ny)/2 && col >= (p.nx-d.nx)/2 && col < (p.nx+d.nx)/2);
    if(d.mode==='perimeter_rows')return row<d.rows || row>=p.ny-d.rows || col<d.rows || col>=p.nx-d.rows;
    if(d.mode==='positions')return !d.omitted.some(([r,c])=>r===row&&c===col);
    throw new RangeError('Unknown depopulation mode');
}

export function gridLayout(p) {
    const contacts=[];
    for(let row=0;row<p.ny;row++)for(let col=0;col<p.nx;col++)if(isPopulated(row,col,p))contacts.push({
        terminal:`${rowLetter(row,p.row_letters)}${col+1}`,row,column:col,
        center_mm:[(col-(p.nx-1)/2)*p.pitch+p.array_offset[0],((p.ny-1)/2-row)*p.pitch+p.array_offset[1],0],
        diameter_mm:p.ball_diameter,reference_basis:'TOP_VIEW_BALL_AXIS_AT_PCB_PLANE'});
    return contacts;
}

export function perimeterLayout(p) {
    const contacts=[];
    for(let s=0;s<4;s++) {
        const count=p.side_counts[s],first=(count-1)*p.pitch/2;
        const radius=p.kind==='plcc'?p.contact_radius : p.kind==='qfp'?(p.lead_span-p.foot_length)/2
            : (s%2?p.body_y:p.body_x)/2-p.pullback-p.foot_length/2;
        for(let i=0;i<count;i++) {
            const t=first-i*p.pitch;
            const xy=[[-radius,t],[-t,-radius],[radius,-t],[t,radius]][s];
            contacts.push({side:SIDES[s],side_index:s,side_position:i,center_mm:[...xy,0],
                size_mm:s%2?[p.lead_width,p.foot_length??p.lead_thickness]:[p.foot_length??p.lead_thickness,p.lead_width]});
        }
    }
    if(p.kind==='plcc'&&p.pin1_mode==='center_top') {
        const start=contacts.findIndex(c=>c.side==='top'&&Math.abs(c.center_mm[0])<1e-8);
        contacts.push(...contacts.splice(0,start));
    }
    return contacts.map((c,i)=>({...c,terminal:String(i+1)}));
}

export function validateQuadGrid(record,p) {
    validateMetadata(record);
    const family={qfp:'PKG-QFP',qfn:'PKG-QFN',dfn:'PKG-DFN',plcc:'PKG-PLCC',bga:'PKG-BGA',wlcsp:'PKG-WLCSP'};
    const generator={qfp:'GEN-QUAD_GULLWING',qfn:'GEN-QFN',dfn:'GEN-QFN',plcc:'GEN-PLCC',bga:'GEN-BGA',wlcsp:'GEN-BGA'};
    if(record.package_family!==family[p.kind] || record.generator!==generator[p.kind] || record.mounting!=='smd'
        || !record.lod_supported.every(l=>LODS.includes(l)))throw new RangeError('Invalid Stage 3 family contract');
    for(const key of ['body_x','body_y','height','pitch','marker_diameter','marker_inset'])positive(p[key],key);
    finite(p.standoff,'standoff');if(p.standoff<0||p.standoff>=p.height)throw new RangeError('Invalid standoff');
    if(p.marker_inset<=p.marker_diameter/2 || p.marker_inset>=Math.min(p.body_x,p.body_y)/2)throw new RangeError('Marker exceeds body');
    if(p.height>p.source_height+1e-8)throw new RangeError('Stack exceeds supplied height limit');
    if(['bga','wlcsp'].includes(p.kind)) {
        for(const n of [p.nx,p.ny])if(!Number.isInteger(n)||n<2||n>32)throw new RangeError('Invalid grid dimensions');
        positive(p.ball_diameter,'ball diameter');rowLetter(0,p.row_letters);
        if(p.coordinate_view!=='TOP'||p.standoff<=0||p.standoff>p.ball_diameter+1e-9||p.ball_diameter>=p.pitch)throw new RangeError('Invalid ball height/pitch/view');
        if(!Array.isArray(p.array_offset)||p.array_offset.length!==2)throw new RangeError('Invalid array offset');
        p.array_offset.forEach(v=>finite(v,'offset'));
        const d=p.depopulate;
        if(d.mode==='center') {
            for(const [cut,size] of [[d.nx,p.nx],[d.ny,p.ny]])if(!Number.isInteger(cut)||cut<=0||cut>=size||(size-cut)%2)throw new RangeError('Centered depopulation must preserve symmetry');
        } else if(d.mode==='perimeter_rows') {
            if(!Number.isInteger(d.rows)||d.rows<1||d.rows>Math.min(p.nx,p.ny)/2)throw new RangeError('Invalid perimeter depth');
        } else if(d.mode==='positions') {
            if(!Array.isArray(d.omitted)||d.omitted.some(a=>!Array.isArray(a)||a.length!==2||a.some(v=>!Number.isInteger(v))||a[0]<0||a[0]>=p.ny||a[1]<0||a[1]>=p.nx))throw new RangeError('Invalid omitted ball positions');
        } else if(d.mode!=='none')throw new RangeError('Unknown depopulation mode');
        const contacts=gridLayout(p);
        if(!contacts.some(c=>c.terminal==='A1'))throw new RangeError('A1 must remain populated');
        for(const c of contacts)for(const [i,size] of [[0,p.body_x],[1,p.body_y]])if(Math.abs(c.center_mm[i])+p.ball_diameter/2>(size-p.grid_margin)/2+1e-8)throw new RangeError('Ball grid exceeds body footprint margin');
        return record;
    }
    if(!Array.isArray(p.side_counts)||p.side_counts.length!==4||p.side_counts.some(n=>!Number.isInteger(n)||n<0)
        ||p.side_counts.reduce((a,b)=>a+b,0)!==p.pin_count)throw new RangeError('Side counts do not sum to terminal count');
    if(p.kind==='dfn' ? p.side_counts[1]!==0||p.side_counts[3]!==0||p.side_counts[0]!==p.side_counts[2]
        : p.side_counts.some(n=>n!==p.pin_count/4))throw new RangeError('Wrong populated sides');
    for(const key of ['lead_width','lead_thickness'])positive(p[key],key);
    if(p.lead_width>=p.pitch)throw new RangeError('Adjacent terminals overlap');
    const margin=p.kind==='qfp'?1:p.kind==='plcc'?2:p.accepted_corner_margin;
    for(let s=0;s<4;s++)if(p.side_counts[s]) {
        const span=(p.side_counts[s]-1)*p.pitch+(p.kind==='qfn'||p.kind==='dfn'?p.lead_width:0);
        if(span>(s%2?p.body_x:p.body_y)-margin+1e-8)throw new RangeError('Pitch/count exceeds body/corner margin');
    }
    if(p.kind==='qfp') {
        if(p.lead_span/2-p.foot_length<=Math.max(p.body_x,p.body_y)/2)throw new RangeError('Lead span cannot accommodate body and foot');
    } else if(p.kind==='plcc') {
        if(!['center_top','section6_topleft'].includes(p.pin1_mode)||p.side_counts.some(n=>n%2!==1))throw new RangeError('Invalid PLCC numbering mode/count');
        const r=p.lead_span/2-p.contact_radius;
        if(r<=p.lead_thickness || r>=p.standoff || p.exit_height<=r || p.exit_height>=p.height
            ||p.bevel_size<=0||p.bevel_size>=Math.min(p.body_x,p.body_y)/3)throw new RangeError('Invalid J curl/bevel geometry');
    } else {
        for(const key of ['ep_x','ep_y','foot_length'])positive(p[key],key);
        finite(p.pullback,'terminal pullback');if(p.pullback<0)throw new RangeError('Negative terminal pullback');
        for(let s=0;s<4;s++)if(p.side_counts[s]) {
            const gap=(s%2?p.body_y:p.body_x)/2-p.pullback-p.foot_length-(s%2?p.ep_y:p.ep_x)/2;
            if(gap<p.accepted_min_gap-1e-8)throw new RangeError('Exposed pad clearance below accepted source geometry');
        }
        if(p.ep_x>=p.body_x||p.ep_y>=p.body_y||p.lead_thickness>=p.height)throw new RangeError('Pad consumes body');
    }
    return record;
}
