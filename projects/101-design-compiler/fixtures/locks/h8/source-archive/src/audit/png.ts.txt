import { inflateSync } from 'node:zlib';
// Minimal strict decoder for Chromium screenshot PNG: 8-bit RGB/RGBA, non-interlaced only.
// No image library/dependency/download; unsupported PNG modes fail, never fabricate metrics.
export function decodeScreenshot(bytes:Uint8Array){
 const b=Buffer.from(bytes);if(b.subarray(0,8).toString('hex')!=='89504e470d0a1a0a')throw new Error('PNG_SIGNATURE');
 let offset=8,width=0,height=0,channels=0,ended=false;const data:Buffer[]=[];
 while(offset<b.length){
  if(offset+12>b.length)throw new Error('PNG_TRUNCATED');const size=b.readUInt32BE(offset),type=b.toString('ascii',offset+4,offset+8);
  if(offset+size+12>b.length)throw new Error('PNG_TRUNCATED');const chunk=b.subarray(offset+8,offset+8+size);
  if(type==='IHDR'){
   if(width||size!==13)throw new Error('PNG_HEADER');width=chunk.readUInt32BE(0);height=chunk.readUInt32BE(4);
   if(chunk[8]!==8||!([2,6].includes(chunk[9]!))||chunk[10]||chunk[11]||chunk[12]||!width||!height||width*height>20000000)throw new Error('PNG_UNSUPPORTED');
   channels=chunk[9]===6?4:3;
  }else if(type==='IDAT')data.push(chunk);else if(type==='IEND'){ended=true;break;}
  offset+=size+12;
 }
 if(!ended||!width||!data.length)throw new Error('PNG_INCOMPLETE');
 const raw=inflateSync(Buffer.concat(data),{maxOutputLength:(width*channels+1)*height});
 const stride=width*channels;if(raw.length!==(stride+1)*height)throw new Error('PNG_SCANLINE_SIZE');
 const decoded=new Uint8Array(width*height*channels),rgba=new Uint8Array(width*height*4);
 const paeth=(a:number,c:number,d:number)=>{const p=a+c-d,pa=Math.abs(p-a),pb=Math.abs(p-c),pc=Math.abs(p-d);return pa<=pb&&pa<=pc?a:pb<=pc?c:d;};
 for(let y=0;y<height;y++){
  const filter=raw[y*(stride+1)]!;if(filter>4)throw new Error('PNG_FILTER');
  for(let x=0;x<stride;x++){
   const index=y*stride+x,left=x>=channels?decoded[index-channels]!:0,up=y?decoded[index-stride]!:0,corner=y&&x>=channels?decoded[index-stride-channels]!:0;
   const delta=filter===0?0:filter===1?left:filter===2?up:filter===3?Math.floor((left+up)/2):paeth(left,up,corner);
   decoded[index]=(raw[y*(stride+1)+1+x]!+delta)&255;
  }
 }
 for(let i=0;i<width*height;i++){rgba[i*4]=decoded[i*channels]!;rgba[i*4+1]=decoded[i*channels+1]!;rgba[i*4+2]=decoded[i*channels+2]!;rgba[i*4+3]=channels===4?decoded[i*channels+3]!:255;}
 return {width,height,pixels:rgba};
}
