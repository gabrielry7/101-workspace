"""Copy the authored browser module, shared validators and contract into the wheel."""
from pathlib import Path
import hashlib
import json
import sys

here=Path(__file__).resolve().parent
web=here.parents[1]/'projects/101_restaurant_commerce_v4/src/world_model/restaurant_commerce/web'
files={name:here/name for name in ['checkout-chassis.js','checkout-chassis.css','checkout-anatomy.js']}
files.update({name:here/'vendor'/name for name in ['checkout-bones.js','checkout-types.js']})
outputs={name:path.read_bytes().replace(b"./vendor/",b"./") for name,path in files.items()}
contract=json.loads((here/'contract.json').read_text())
contract['fonts']['inter']=json.loads((here/'vendor/typography.json').read_text())['sans']
outputs['checkout-contract.json']=(json.dumps(contract,ensure_ascii=False,indent=2)+'\n').encode()
outputs['checkout-contract.js']=('export default '+json.dumps(json.loads(outputs['checkout-contract.json']),ensure_ascii=False)+';\n').encode()
if '--check' in sys.argv:
    assert (here/'checkout-contract.js').read_bytes()==outputs['checkout-contract.js']
else:
    (here/'checkout-contract.js').write_bytes(outputs['checkout-contract.js'])
for name,data in outputs.items():
    target=web/name
    if '--check' in sys.argv:
        assert target.read_bytes()==data, f'Stale runtime {name}'
    else: target.write_bytes(data)
print(json.dumps({name:hashlib.sha256(data).hexdigest() for name,data in outputs.items()},indent=2))
