export function tone(status){const value=(status||"UNKNOWN").toUpperCase();if(value==="PASS")return"pass";if(value.includes("FAIL")||value.includes("ERROR")||value.includes("BLOCK"))return"fail";if(value.includes("NOT_YET")||value.includes("UNSUPPORTED"))return"notyet";return"warn"}
export function badge(status){const safe=String(status||"UNKNOWN").replaceAll("_"," ");return `<span class="badge ${tone(status)}">${escapeHtml(safe)}</span>`}
export function money(value,knowledge="KNOWN"){return knowledge==="UNKNOWN"||value==null?"UNKNOWN":`$${Number(value).toFixed(2)}`}
export function artifactCurrent(item){return item?.current===true?"CURRENT":"STALE"}
export function releaseReadiness(release){const current=release?.current===true,status=current?String(release?.status||"UNKNOWN"):"STALE";return{status,label:current&&status==="READY_FOR_MANUFACTURING_REVIEW"?"Ready for manufacturing review":"Release is stale or not ready"}}
export function escapeHtml(value){return String(value??"").replace(/[&<>'"]/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char]))}
