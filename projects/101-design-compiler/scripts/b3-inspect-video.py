"""Decode comparison of already licensed local bytes. No network or encoding."""
import cv2, hashlib, json, pathlib, sys
source = pathlib.Path('.tools/b2-demo/originals/149678.mp4')
output = pathlib.Path('public/media/b3-experience/149678-silent-1280.mp4')
a, b = cv2.VideoCapture(str(source)), cv2.VideoCapture(str(output))
if not a.isOpened() or not b.isOpened(): raise RuntimeError('VIDEO_DECODE_OPEN_FAILED')
frames = []
while True:
    ok_a, x = a.read(); ok_b, y = b.read()
    if ok_a != ok_b: raise RuntimeError('VIDEO_FRAME_COUNT_CHANGED')
    if not ok_a: break
    hx, hy = hashlib.sha256(x.tobytes()).hexdigest(), hashlib.sha256(y.tobytes()).hexdigest()
    if x.shape != (720, 1280, 3) or x.shape != y.shape or hx != hy: raise RuntimeError('VIDEO_PIXELS_CHANGED')
    frames.append(hx)
fps = b.get(cv2.CAP_PROP_FPS)
a.release(); b.release()
if len(frames) != 234 or fps != 25: raise RuntimeError('VIDEO_TIMING_CHANGED')
result = dict(kind='ACTUAL_SOURCE_OUTPUT_DECODE_COMPARISON', source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
              output_sha256=hashlib.sha256(output.read_bytes()).hexdigest(), decoded_frames=len(frames), fps=fps,
              width=1280, height=720, duration_seconds=len(frames)/fps, all_decoded_pixels_identical=True,
              frame_sha256=frames, opencv=cv2.__version__, python=sys.version.split()[0],
              limit='Technical pixel equality, not a new legal permission or full visual endorsement')
path = pathlib.Path('docs/evidence/corrections/b3/experience-media-01/decode.json')
if '--record' in sys.argv:
    if path.exists(): raise RuntimeError('DECODE_RECEIPT_EXISTS')
    path.write_text(json.dumps(result, indent=2)+'\n', encoding='utf8')
elif '--verify' in sys.argv:
    if json.loads(path.read_text(encoding='utf8')) != result: raise RuntimeError('DECODE_REPLAY_MISMATCH')
else: raise RuntimeError('EXPLICIT_RECORD_OR_VERIFY_REQUIRED')
print(json.dumps({k: result[k] for k in ['decoded_frames','width','height','duration_seconds','all_decoded_pixels_identical']}))
