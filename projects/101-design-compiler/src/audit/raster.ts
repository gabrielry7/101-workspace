// Deterministic raster instrument. Executes in Chromium; no AI vision, aesthetic score, or image transformation.
// Mask the original photograph's box: analyze layout/text pixels only, never infer stock content.
export function measurePixels(pixels:Uint8Array|Uint8ClampedArray,width:number,height:number,mediaBox:{x:number;y:number;width:number;height:number}|null){
 if(pixels.length!==width*height*4)throw new Error('RASTER_DIMENSION_MISMATCH');
 const bins=Array.from({length:16},()=>0);let sampled=0,ignored=0,ink=0,edges=0,pairs=0,xSum=0,ySum=0;
 const luminance=(i:number)=>.2126*pixels[i]!+.7152*pixels[i+1]!+.0722*pixels[i+2]!;
 const masked=(x:number,y:number)=>mediaBox&&x>=mediaBox.x&&x<=mediaBox.x+mediaBox.width&&y>=mediaBox.y&&y<=mediaBox.y+mediaBox.height;
 for(let y=0;y<height;y+=4)for(let x=0;x<width;x+=4){
  if(masked(x,y)){ignored++;continue;}
  const index=(y*width+x)*4,l=luminance(index);sampled++;bins[Math.min(15,Math.floor(l/16))]!++;
  if(l<150){ink++;xSum+=x;ySum+=y;}
  if(x+4<width&&!masked(x+4,y)){pairs++;if(Math.abs(l-luminance(index+16))>40)edges++;}
 }
 const entropy=bins.reduce((n,b)=>b? n-(b/sampled)*Math.log2(b/sampled):n,0);
 return {status:'MEASURED_AUXILIARY' as const,width,height,sampling_stride:4,masked_region:'ORIGINAL_MEDIA_BOX',
  sampled_pixels:sampled,ignored_media_pixels:ignored,ink_ratio:ink/sampled,edge_density:pairs?edges/pairs:0,entropy_bits:entropy,
  centroid:ink?{x:xSum/ink/width,y:ySum/ink/height}:null,
  limitations:'Fixed luminance thresholds on text/layout pixels only; not beauty, semantic saliency or human preference.'};
}
export async function measureRaster(base64:string,mediaBox:{x:number;y:number;width:number;height:number}|null){
 const image=new Image();image.src='data:image/png;base64,'+base64;await image.decode();
 const canvas=document.createElement('canvas');canvas.width=image.naturalWidth;canvas.height=image.naturalHeight;
 const context=canvas.getContext('2d')!;context.drawImage(image,0,0);
 return measurePixels(context.getImageData(0,0,canvas.width,canvas.height).data,canvas.width,canvas.height,mediaBox);
}
