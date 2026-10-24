import {z} from 'zod';
import {inputSha256} from '../upstream/v1/protocol.ts';
const sha=z.string().regex(/^[a-f0-9]{64}$/);
const BoundContext=z.strictObject({plan:sha,content:sha,media:sha,context:sha});
// DOM serializers may reorder object keys. Values, not insertion order, bind
// a render to its source. Missing or additional fields cannot compare equal.
export function sameReferenceContext(a:unknown,b:unknown){
 const x=BoundContext.safeParse(a),y=BoundContext.safeParse(b);
 return x.success&&y.success&&inputSha256(x.data)===inputSha256(y.data);
}
