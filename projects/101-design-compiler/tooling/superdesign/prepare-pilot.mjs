// Export an actual built B3 home for layout-only inference. No media bytes leave here.
import {readFile, writeFile, mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {resolve, dirname, sep} from 'node:path';
import {fileURLToPath} from 'node:url';
const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const tmp = resolve(root, '.superdesign/tmp');
const sourcePath = 'dist/b3/candidate-01/index.html';
const source = await readFile(resolve(root, sourcePath), 'utf8');
if (!source.includes('data-profile-id="candidate-01"') || !source.includes('data-page-kind="home"')) throw Error('WRONG_HOME');
const sha = s => createHash('sha256').update(s).digest('hex');
const attrs = tag => Object.fromEntries([...tag.matchAll(/([\w:-]+)="([^"]*)"/g)].map(m => [m[1],m[2]]));
const media = [], links = [];
const placeholder = 'data:image/svg+xml;base64,' + Buffer.from('<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="960"><rect width="1280" height="960" fill="#d0d0cb"/></svg>').toString('base64');
let html = source.replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, '');
html = html.replace(/<(?:img|source|video)\b[^>]*>/gi, tag => {
  const a = attrs(tag), key = `media-${media.length + 1}`;
  media.push({key, originalTag:tag, originalAttributes:a});
  let safe = tag.replace(/\s(?:src|srcset|poster|data-src)="[^"]*"/gi,'');
  safe = safe.replace(/\sautoplay\b/gi,'');
  const extra = tag.startsWith('<img') ? ` src="${placeholder}"` : tag.startsWith('<video') ? ` poster="${placeholder}"` : '';
  return safe.replace(/>$/,` data-pilot-media="${key}"${extra}>`);
});
html = html.replace(/<a\b[^>]*>/gi, tag => {
  const a = attrs(tag), key = `pilot-link-${links.length + 1}`;
  links.push({key, href:a.href, originalTag:tag});
  let safe = a.id ? tag : tag.replace(/^<a/,`<a id="${key}"`);
  if (a.href && !a.href.startsWith('https://') && !a.href.startsWith('#')) safe = safe.replace(/\bhref="[^"]*"/,`href="#${key}"`);
  return safe;
});
// Inline the existing build CSS rather than make the remote service fetch localhost.
for (const m of [...html.matchAll(/<link\b[^>]*rel="stylesheet"[^>]*>/gi)]) {
  const href=attrs(m[0]).href;
  if (!href?.startsWith('/_astro/')) throw Error('UNEXPECTED_STYLESHEET');
  const path=resolve(root,'dist',href.slice(1));
  if(!path.startsWith(resolve(root,'dist')+sep)) throw Error('STYLESHEET_PATH_REJECTED');
  html=html.replace(m[0],`<style>${await readFile(path,'utf8')}</style>`);
}
html=html.replace(/body>main#contenido/g,'#pilot-document>main#contenido').replace(/body>\.skip/g,'#pilot-document>.skip');
html=html.replace(/<body\b[^>]*>/,'<body><div id="pilot-document">').replace('</body>','</div></body>');
html=html.replace('</head>','<meta name="pilot-media-mode" content="GEOMETRY_ONLY_NO_LICENSED_MEDIA_UPLOADED"></head>');
if (/<(?:img|source|video)\b[^>]*(?:src|srcset|poster|data-src)="(?!data:)[^"]+"/i.test(html)) throw Error('MEDIA_URI_LEAK');
if (/<script\b/i.test(html) || /(?:localhost|127\.0\.0\.1|file:\/\/|[A-Z]:\\)/i.test(html)) throw Error('UNEXPECTED_REMOTE_CONTEXT');
const navigation=html.match(/<header\b[\s\S]*?<\/header>/)?.[0];
const footer=html.match(/<footer\b[\s\S]*?<\/footer>/)?.[0];
if(!navigation || !footer || media.filter(m=>m.originalTag.startsWith('<img')).length!==5) throw Error('HOME_BINDINGS_MISSING');
await mkdir(tmp,{recursive:true});
await writeFile(resolve(tmp,'current-home.geometry.html'),html);
await writeFile(resolve(tmp,'navigation.html'),navigation);
await writeFile(resolve(tmp,'footer.html'),footer);
await writeFile(resolve(tmp,'local-bindings.json'),JSON.stringify({schemaVersion:1,sourcePath,sourceSha256:sha(source),payloadSha256:sha(html),mode:'GEOMETRY_ONLY_NO_LICENSED_MEDIA_UPLOADED',media,links},null,2)+'\n');
console.log(JSON.stringify({status:'PAYLOAD_READY',sourcePath,sourceSha256:sha(source),payloadSha256:sha(html),payloadBytes:Buffer.byteLength(html),mediaBindings:media.length,imageBindings:5,links:links.length,uploadedMediaBytes:0}));
