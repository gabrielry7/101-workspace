import sharp from 'sharp';
export async function capturePresence(bytes:Uint8Array){
 const m=await sharp(bytes).metadata();if(!m.width||!m.height)throw Error('CAPTURE_DIMENSIONS_MISSING');
 const cropped=await sharp(bytes).extract({left:Math.floor(m.width*.1),top:Math.floor(m.height*.1),width:Math.floor(m.width*.8),height:Math.floor(m.height*.8)}).resize(160,160,{fit:'fill'}).removeAlpha().toBuffer();
 const grayImage=await sharp(cropped).greyscale().toBuffer(),stats=await sharp(grayImage).stats(),luma=await sharp(grayImage).raw().toBuffer(),raw=await sharp(cropped).raw().toBuffer({resolveWithObject:true});let gray=0,edges=0;
 for(let n=0;n<raw.data.length;n+=raw.info.channels){const r=raw.data[n]!,g=raw.data[n+1]!,b=raw.data[n+2]!;if(Math.max(r,g,b)-Math.min(r,g,b)<=2&&r>60&&r<245)gray++;}
 const gray_fraction=gray/(raw.info.width*raw.info.height),entropy=stats.entropy,stdev=stats.channels[0]!.stdev;
 for(let y=0;y<160;y++)for(let x=1;x<160;x++)if(Math.abs(luma[y*160+x]!-luma[y*160+x-1]!)>12)edges++;
 const horizontal_edge_fraction=edges/(160*159);
 return {success:entropy>=.25&&stdev>=3&&gray_fraction<=.65&&(entropy>=2||horizontal_edge_fraction>.0005),entropy,stdev,gray_fraction,horizontal_edge_fraction,width:m.width,height:m.height};
}
