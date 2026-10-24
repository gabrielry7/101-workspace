"""Explicit local video-only derivation with already installed OpenCV; no provider calls."""
import sys, json, hashlib, pathlib, cv2
if '--reviewed-silent-output' not in sys.argv:
    raise RuntimeError('EXPLICIT_VIDEO_DERIVATION_REQUIRED')
source = pathlib.Path('.tools/b2-demo/originals/149678.mp4')
output = pathlib.Path('public/media/b2-fictional/149678-silent-640.webm')
receipt = pathlib.Path('docs/evidence/corrections/b2-demo/video-derivation-640.json')
if receipt.exists():
    raise RuntimeError('VIDEO_DERIVATION_ALREADY_RECORDED')
capture = cv2.VideoCapture(str(source))
if not capture.isOpened():
    raise RuntimeError('SOURCE_NOT_DECODABLE')
fps = capture.get(cv2.CAP_PROP_FPS)
width, height = 640, 360
writer = cv2.VideoWriter(str(output), cv2.VideoWriter_fourcc(*'VP80'), fps, (width, height))
if not writer.isOpened():
    raise RuntimeError('LOCAL_VP8_ENCODER_UNAVAILABLE')
frames, samples = 0, []
folder = pathlib.Path('.tools/b2-demo/video-review')
folder.mkdir(parents=True, exist_ok=True)
while True:
    ok, frame = capture.read()
    if not ok:
        break
    writer.write(cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA))  # Pixels only, no audio.
    if frames % max(1, round(fps)) == 0:
        path = folder / f'original-{frames:04}.jpg'
        cv2.imwrite(str(path), frame)
        samples.append({'frame': frames, 'seconds': frames/fps, 'path': str(path).replace('\\', '/')})
    frames += 1
capture.release()
writer.release()
decoded = cv2.VideoCapture(str(output))
count, sample_hashes = 0, []
while True:
    ok, frame = decoded.read()
    if not ok:
        break
    if count % max(1, round(fps)) == 0:
        path = folder / f'derived-{count:04}.jpg'
        cv2.imwrite(str(path), frame)
        sample_hashes.append({'frame': count, 'seconds': count/fps, 'pixels_sha256': hashlib.sha256(frame.tobytes()).hexdigest(), 'path': str(path).replace('\\', '/')})
    count += 1
decoded.release()
if count != frames or frames < 2:
    raise RuntimeError('DERIVATION_FRAME_COUNT_MISMATCH')
digest = lambda p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
binary = next(pathlib.Path(cv2.__file__).parent.glob('*.pyd'))
data = {'kind':'VIDEO_ONLY_PIXEL_TRANSCODE', 'source':str(source).replace('\\','/'), 'source_sha256':digest(source),
        'output':str(output).replace('\\','/'), 'output_sha256':digest(output), 'output_bytes':output.stat().st_size,
        'tool':{'python':sys.version, 'opencv':cv2.__version__, 'opencv_binary':str(binary), 'opencv_sha256':digest(binary), 'encoder':'VP80'},
        'width':width,'height':height,'fps':fps,'source_frames_decoded':frames,'output_frames_decoded':count,
        'duration_from_frames':frames/fps, 'audio_input':'NOT_PASSED_TO_WRITER', 'audio_output':'REQUIRES_CONTAINER_VERIFICATION',
        'source_samples':samples,'output_samples':sample_hashes,
        'limits':['No source audio listening/rights approval','One-frame-per-second visual review is separate from full technical decode','Original retained privately; only silent derivative may be admitted','Encoded bytes pinned; recipe is not claimed portable or bit-identical across encoders']}
receipt.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'frames':frames,'fps':fps,'width':width,'height':height,'bytes':output.stat().st_size,'sha256':digest(output)}))
