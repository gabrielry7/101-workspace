const fs=require('node:fs'),path=require('node:path'),z=require('node:zlib'),Module=require('node:module');
const f=path.join(__dirname,'renderer-v2.cjs'),m=new Module(f,module);m.filename=f;m.paths=[];
m._compile(z.gunzipSync(fs.readFileSync(path.join(__dirname,'renderer-v2.cjs.gz')),{maxOutputLength:8000000}).toString('utf8'),f);
