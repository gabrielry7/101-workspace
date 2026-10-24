import {createHash} from 'node:crypto';
import {mp4Handlers} from './video-tracks.ts';
type Box={type:string;start:number;payload:number;end:number};
function boxes(b:Buffer,start=0,end=b.length):Box[]{const out:Box[]=[];let p=start;while(p<end){if(p+8>end)throw Error('REMUX_BOX_TRUNCATED');let size=b.readUInt32BE(p),header=8;if(size===1){size=Number(b.readBigUInt64BE(p+8));header=16;}if(size===0)size=end-p;if(size<header||p+size>end)throw Error('REMUX_BOX_BOUNDARY');out.push({type:b.toString('ascii',p+4,p+8),start:p,payload:p+header,end:p+size});p+=size;}return out;}
const box=(type:string,payload:Buffer)=>{const b=Buffer.alloc(8);b.writeUInt32BE(payload.length+8);b.write(type,4,'ascii');return Buffer.concat([b,payload]);};
// Narrow MP4 remuxer for the reviewed local source, not a general encoder.
// It copies video chunks bit-for-bit, drops every other track and all orphan
// mdat bytes, and rebuilds chunk offsets. No audio bytes are carried forward.
export function videoOnlyMp4(source:Buffer){
 const top=boxes(source),moov=top.find(b=>b.type==='moov'),ftyp=top.find(b=>b.type==='ftyp'),mdats=top.filter(b=>b.type==='mdat');if(!moov||!ftyp||!mdats.length)throw Error('REMUX_SOURCE_INVALID');
 const children=(p:Box)=>boxes(source,p.payload,p.end),get=(p:Box,t:string)=>{const b=children(p).find(b=>b.type===t);if(!b)throw Error(`REMUX_MISSING_${t}`);return b;};
 const tracks=children(moov).filter(b=>b.type==='trak'),videos=tracks.filter(t=>{const h=get(get(t,'mdia'),'hdlr');return source.toString('ascii',h.payload+8,h.payload+12)==='vide';});if(videos.length!==1)throw Error('REMUX_EXPECT_ONE_VIDEO');
 const video=videos[0]!,stbl=get(get(get(video,'mdia'),'minf'),'stbl'),stco=children(stbl).find(b=>b.type==='stco'||b.type==='co64')!,stsc=get(stbl,'stsc'),stsz=get(stbl,'stsz');
 if(!stco)throw Error('REMUX_CHUNK_OFFSETS_MISSING');const stride=stco.type==='co64'?8:4;
 const count=source.readUInt32BE(stco.payload+4),fixed=source.readUInt32BE(stsz.payload+4),samples=source.readUInt32BE(stsz.payload+8),entries=source.readUInt32BE(stsc.payload+4);
 if(!count||!samples||!entries||stco.payload+8+count*stride!==stco.end||stsc.payload+8+entries*12!==stsc.end||stsz.payload+12+(fixed?0:samples*4)!==stsz.end)throw Error('REMUX_SAMPLE_TABLE_INVALID');
 const runs=Array.from({length:entries},(_,i)=>({first:source.readUInt32BE(stsc.payload+8+i*12),samples:source.readUInt32BE(stsc.payload+12+i*12)}));if(runs[0]!.first!==1||runs.some((r,i)=>!r.samples||(i>0&&r.first<=runs[i-1]!.first)))throw Error('REMUX_CHUNK_RUN_INVALID');
 let sample=0;const chunks:Buffer[]=[],relative:number[]=[];let bytes=0;
 for(let i=0;i<count;i++){const run=runs.findLast(r=>r.first<=i+1)!;let length=0;for(let n=0;n<run.samples;n++){if(sample>=samples)throw Error('REMUX_SAMPLE_OVERFLOW');length+=fixed||source.readUInt32BE(stsz.payload+12+sample*4);sample++;}const start=stride===8?Number(source.readBigUInt64BE(stco.payload+8+i*8)):source.readUInt32BE(stco.payload+8+i*4);if(!mdats.some(m=>start>=m.payload&&start+length<=m.end))throw Error('REMUX_CHUNK_OUTSIDE_MDAT');relative.push(bytes);chunks.push(source.subarray(start,start+length));bytes+=length;}
 if(sample!==samples)throw Error('REMUX_SAMPLE_COVERAGE');
 const containers=new Set(['moov','trak','mdia','minf','stbl']);
 const rebuild=(p:Box,base:number):Buffer=>{if(p.start===stco.start){const payload=Buffer.from(source.subarray(p.payload,p.end));relative.forEach((n,i)=>stride===8?payload.writeBigUInt64BE(BigInt(base+n),8+i*8):payload.writeUInt32BE(base+n,8+i*4));return box(p.type,payload);}if(containers.has(p.type))return box(p.type,Buffer.concat(children(p).filter(c=>p.type!=='moov'||c.type!=='trak'||c.start===video.start).map(c=>rebuild(c,base))));return source.subarray(p.start,p.end);};
 const f=source.subarray(ftyp.start,ftyp.end),placeholder=rebuild(moov,0),mdat=Buffer.concat(chunks),output=Buffer.concat([f,rebuild(moov,f.length+placeholder.length+8),box('mdat',mdat)]);
 if(JSON.stringify(mp4Handlers(output))!=='["vide"]')throw Error('REMUX_AUDIO_TRACK_REMAINS');
 const tkhd=get(video,'tkhd');return {output,samples,width:source.readUInt32BE(tkhd.end-8)/65536,height:source.readUInt32BE(tkhd.end-4)/65536,video_payload_bytes:bytes,video_payload_sha256:createHash('sha256').update(mdat).digest('hex')};
}
