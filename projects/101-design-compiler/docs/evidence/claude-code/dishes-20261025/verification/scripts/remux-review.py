import cv2,json,pathlib,hashlib,numpy as np,subprocess,imageio_ffmpeg
folder=pathlib.Path('.tools/claude-code/dish-resources-20261025');records=[];ffmpeg=imageio_ffmpeg.get_ffmpeg_exe();items=json.loads((folder/'acquisition.json').read_text(encoding='utf-8'))['files']
for item in [i for i in items if i['id']!=33256]:
 ident=item['id'];source=pathlib.Path(item['original']['path']);output=folder/f'assets/{ident}-silent.mp4'
 result=subprocess.run([ffmpeg,'-y','-i',str(source),'-map','0:v:0','-c:v','copy','-an','-sn','-dn','-map_metadata','-1','-movflags','+faststart',str(output)],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
 if result.returncode:raise RuntimeError('VIDEO_ONLY_REMUX_FAILED')
 cap=cv2.VideoCapture(str(source));check=cv2.VideoCapture(str(output));fps=cap.get(cv2.CAP_PROP_FPS);sw=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH));sh=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT));frames=0;samples=[]
 while True:
  a,frame=cap.read();b,other=check.read()
  if a!=b:raise RuntimeError('FRAME_COUNT')
  if not a:break
  if not np.array_equal(frame,other):raise RuntimeError('VIDEO_PIXELS_CHANGED')
  if frames%max(1,round(fps*1.5))==0:
   tile=np.full((240,360,3),235,dtype=np.uint8);r=min(360/sw,220/sh);tw=int(sw*r);th=int(sh*r);tile[0:th,(360-tw)//2:(360-tw)//2+tw]=cv2.resize(frame,(tw,th));cv2.putText(tile,f'{ident} / {frames/fps:.1f}s',(8,235),cv2.FONT_HERSHEY_SIMPLEX,.5,(25,25,25),1);samples.append(tile)
  frames+=1
 cap.release();check.release();rows=(len(samples)+3)//4;canvas=np.full((rows*240,1440,3),255,dtype=np.uint8)
 for i,frame in enumerate(samples):canvas[i//4*240:(i//4+1)*240,i%4*360:(i%4+1)*360]=frame
 cv2.imwrite(str(folder/f'{ident}-sheet.jpg'),canvas)
 records.append({'id':ident,'path':str(output).replace('\\','/'),'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'bytes':output.stat().st_size,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'width':sw,'height':sh,'source_frames_decoded':frames,'output_frames_decoded':frames,'every_decoded_frame_pixel_identical':True,'fps':fps,'duration':frames/fps,'audio':'NONE_VIDEO_ONLY_FFMPEG_REMUX','sample_interval_seconds':1.5,'codec':'avc1'})
(folder/'remux-reviewed.json').write_text(json.dumps(records,indent=2),encoding='utf-8');print(json.dumps(records))
