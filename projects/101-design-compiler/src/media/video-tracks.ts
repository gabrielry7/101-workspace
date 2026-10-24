// Narrow structural readers for the actual local MP4 source and WebM derivative.
// No claim of a general codec validator; full decode/browser inspection is separate.
export function mp4Handlers(b:Buffer){
 const boxes=(start:number,end:number)=>{const out:{type:string;start:number;end:number}[]=[];
  for(let p=start;p+8<=end;){let n=b.readUInt32BE(p),h=8;if(n===1){if(p+16>end)throw Error('INVALID_MP4');n=Number(b.readBigUInt64BE(p+8));h=16;}if(n===0)n=end-p;
   if(n<h||p+n>end)throw Error('INVALID_MP4');out.push({type:b.toString('ascii',p+4,p+8),start:p+h,end:p+n});p+=n;}return out;};
 const moov=boxes(0,b.length).find(x=>x.type==='moov');if(!moov)throw Error('MP4_MOOV_MISSING');
 return boxes(moov.start,moov.end).filter(x=>x.type==='trak').map(t=>{const m=boxes(t.start,t.end).find(x=>x.type==='mdia');if(!m)throw Error('MP4_MDIA_MISSING');
  const h=boxes(m.start,m.end).find(x=>x.type==='hdlr');if(!h||h.start+12>h.end)throw Error('MP4_HDLR_MISSING');return b.toString('ascii',h.start+8,h.start+12);});
}
export function webmTracks(b:Buffer){
 const vint=(p:number,id=false)=>{if(p>=b.length||!b[p])throw Error('INVALID_EBML');let n=1,mask=128;while(!(b[p]!&mask)){mask>>=1;n++;}if(n>8||p+n>b.length)throw Error('INVALID_EBML');
  let value=BigInt(id?b[p]!:b[p]!&(mask-1));for(let i=1;i<n;i++)value=(value<<8n)|BigInt(b[p+i]!);return {n,value,unknown:!id&&value===(1n<<BigInt(7*n))-1n};};
 const elements=(start:number,end:number)=>{const out:{id:number;start:number;end:number}[]=[];for(let p=start;p<end;){const id=vint(p,true),size=vint(p+id.n),s=p+id.n+size.n,e=size.unknown?end:s+Number(size.value);
   if(e>end||e<s)throw Error('INVALID_EBML_BOUNDARY');out.push({id:Number(id.value),start:s,end:e});p=e;}return out;};
 const segment=elements(0,b.length).find(e=>e.id===0x18538067);if(!segment)throw Error('WEBM_SEGMENT_MISSING');
 const tracks=elements(segment.start,segment.end).find(e=>e.id===0x1654ae6b);if(!tracks)throw Error('WEBM_TRACKS_MISSING');
 return elements(tracks.start,tracks.end).filter(e=>e.id===0xae).map(t=>{const fields=elements(t.start,t.end),type=fields.find(e=>e.id===0x83),codec=fields.find(e=>e.id===0x86);
  if(!type||!codec||type.end-type.start!==1)throw Error('WEBM_TRACK_ENTRY_INVALID');return {type:b[type.start]!,codec:b.toString('ascii',codec.start,codec.end)};});
}
