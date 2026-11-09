# Provision the dedicated project described by the existing private trial state.
# OAuth is read through gcloud; credentials stay in memory and ignored private files.
import datetime,json,pathlib,re,subprocess,time,urllib.request,urllib.error
root=pathlib.Path(__file__).resolve().parents[2]
folder=root/'.tools/honorato-google-live'
state_path=folder/'cloud-state.json'
state=json.loads(state_path.read_text())
if state.get('budget_usd')!=1 or state.get('max_initializations')!=10:
 raise RuntimeError('Dedicated trial state with the authorized US$1 / 10-load scope required')
token=subprocess.check_output(['gcloud','auth','print-access-token'],text=True).strip()
def save():
 state_path.write_text(json.dumps(state,indent=2)+'\n');state_path.chmod(0o600)
def request(url,body=None,method=None):
 data=None if body is None else json.dumps(body).encode()
 req=urllib.request.Request(url,data=data,method=method,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json','X-Goog-User-Project':state['project_id']})
 try:
  with urllib.request.urlopen(req,timeout=40) as response:return json.load(response)
 except urllib.error.HTTPError as error:
  message=json.loads(error.read()).get('error',{}).get('message','Request rejected')
  raise RuntimeError('Cloud HTTP '+str(error.code)+': '+re.sub(r'AIza[A-Za-z0-9_-]+','[REDACTED]',message)) from None
def value(obj,*names):
 return next((obj[n] for n in names if n in obj),None)
project=state['project_id'];number=state['project_number']
base='https://mapmanagement.googleapis.com/v2beta/projects/'+project
# Discovery reads and exact saved evidence precede writes.
styles=request(base+'/styleConfigs')
print('Map Management access verified.',flush=True)
quota=request('https://serviceusage.googleapis.com/v1beta1/projects/'+number+'/services/maps-backend.googleapis.com/consumerQuotaMetrics?view=FULL')
(folder/'quota-readback.json').write_text(json.dumps(quota,indent=2)+'\n')
print('Read Maps JavaScript effective quotas.',flush=True)

# Use the actual service-returned daily limit; never invent a quota resource name.
metric=next(m for m in quota['metrics'] if m['metric']=='maps-backend.googleapis.com/billable_default')
daily=next(limit for limit in metric['consumerQuotaLimits'] if limit['unit']=='1/d/{project}')
if not daily.get('quotaBuckets'):raise RuntimeError('Daily Maps quota buckets unavailable')
if not all(bucket.get('effectiveLimit')=='10' for bucket in daily['quotaBuckets']):
 operation=request('https://serviceusage.googleapis.com/v1beta1/'+daily['name']+'/consumerOverrides?forceOnly=LIMIT_DECREASE_PERCENTAGE_TOO_HIGH',{'overrideValue':'10'})
 for _ in range(60):
  if operation.get('done'):break
  time.sleep(1);operation=request('https://serviceusage.googleapis.com/v1beta1/'+operation['name'])
 if not operation.get('done') or operation.get('error'):raise RuntimeError('Daily Maps quota override did not complete')
 verified=request('https://serviceusage.googleapis.com/v1beta1/'+daily['name'])
 if not verified.get('quotaBuckets') or not all(bucket.get('effectiveLimit')=='10' for bucket in verified['quotaBuckets']):raise RuntimeError('Daily Maps quota readback mismatch')
 print('Daily Maps loads quota restricted to 10 and verified.',flush=True)
state['daily_maps_limit']=10;state['daily_quota_resource']=daily['name'];save()

style=json.loads((root/'tooling/bones/google-no-pois.style.json').read_text())
if 'style_resource' not in state:
 resource=request(base+'/styleConfigs',{'display_name':'101 Honorato - sin lugares ajenos','description':'Local trial: keep streets and geography, hide POI text/icons and transit labels.','json_style_sheet':json.dumps(style)})
 state['style_resource']=resource['name'];save()
 print('Created style resource.',flush=True)
style_resource=request('https://mapmanagement.googleapis.com/v2beta/'+state['style_resource'])
actual=json.loads(value(style_resource,'jsonStyleSheet','json_style_sheet'))
def normalized_style(value):
 return {**value,'styles':sorted(value['styles'],key=lambda item:item['id'])}
if normalized_style(actual)!=normalized_style(style):raise RuntimeError('Stored cloud style differs from requested JSON')
if 'map_resource' not in state:
 resource=request(base+'/mapConfigs',{'display_name':'101 Honorato local vector map','description':'Single-business trial; browser restricted to localhost:8780.','map_type':'VECTOR'})
 state['map_resource']=resource['name'];state['map_id']=value(resource,'mapId','map_id');save()
 print('Created vector Map ID.',flush=True)
if 'context_resource' not in state:
 resource=request('https://mapmanagement.googleapis.com/v2beta/'+state['map_resource']+'/mapContextConfigs',{'map_config':state['map_resource'],'style_config':state['style_resource'],'map_variants':['ROADMAP']})
 state['context_resource']=resource['name'];save()
 print('Associated cloud style to Map ID.',flush=True)
context=request('https://mapmanagement.googleapis.com/v2beta/'+state['context_resource'])
if value(context,'styleConfig','style_config')!=state['style_resource']:raise RuntimeError('Map/style association readback mismatch')
allowed=['http://127.0.0.1:8780','http://127.0.0.1:8780/*','http://localhost:8780','http://localhost:8780/*']
if 'key_resource' not in state:
 operation=request('https://apikeys.googleapis.com/v2/projects/'+number+'/locations/global/keys?keyId=honorato-local-trial',{'displayName':'101 Honorato local browser trial','restrictions':{'apiTargets':[{'service':'maps-backend.googleapis.com'}],'browserKeyRestrictions':{'allowedReferrers':allowed}}})
 for _ in range(60):
  if operation.get('done'):break
  time.sleep(1);operation=request('https://apikeys.googleapis.com/v2/'+operation['name'])
 if not operation.get('done') or operation.get('error'):raise RuntimeError('API key creation did not complete successfully')
 state['key_resource']=operation['response']['name'];save()
 print('Created API-restricted browser key.',flush=True)
key=request('https://apikeys.googleapis.com/v2/'+state['key_resource'])
restrictions=key['restrictions']
if restrictions.get('apiTargets')!=[{'service':'maps-backend.googleapis.com'}] or set(restrictions['browserKeyRestrictions']['allowedReferrers'])!=set(allowed):raise RuntimeError('Browser key restrictions readback mismatch')
secret=request('https://apikeys.googleapis.com/v2/'+state['key_resource']+'/keyString')['keyString']
config={'enabled':True,'apiKey':secret,'mapId':state['map_id'],'styleReview':{'mapId':state['map_id'],'pois':'none','reference':'https://mapmanagement.googleapis.com/v2beta/'+state['style_resource'],'reviewedAt':datetime.datetime.now(datetime.timezone.utc).isoformat()}}
p=folder/'browser-config.json';p.write_text(json.dumps(config,indent=2)+'\n');p.chmod(0o600)
state['configuration_verified_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();state['allowed_referrers']=allowed;save()
print('Configuration saved privately. No key or OAuth token printed. No billable map load performed.',flush=True)
