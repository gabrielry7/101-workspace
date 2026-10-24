import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { resolve, relative, isAbsolute } from 'node:path';
import type { MediaManifest } from './contracts.ts';
import { PackageProof } from './contracts.ts';

export const byteSha256 = (bytes: Uint8Array) => createHash('sha256').update(bytes).digest('hex');
export async function readPackageFile(path: string, root = process.cwd()) {
  const absolute = resolve(root, path), rel = relative(root, absolute);
  if (rel.startsWith('..') || isAbsolute(rel)) throw new Error('PACKAGE_PATH_OUTSIDE_WORKSPACE');
  return readFile(absolute);
}
// Offline evidence verification: compare actual bytes and rendered HTML/browser receipt.
// Official source authenticity was checked at acquisition; no network permission is invented here.
export async function verifyPackageFiles(value: unknown, manifest: MediaManifest, root = process.cwd()) {
  const codes: string[] = [];
  try {
    const proof = PackageProof.parse(value);
    if (proof.client_id !== manifest.client_id || proof.project_id !== manifest.project_id || proof.evaluated_at !== manifest.evaluated_at) codes.push('PACKAGE_CONTEXT_MISMATCH');
    for (const file of proof.files) {
      if (byteSha256(await readPackageFile(file.path, root)) !== file.sha256) codes.push('PACKAGE_FILE_HASH_MISMATCH');
      const asset = manifest.assets.find(a => a.id === file.asset_id);
      if (!asset || asset.data_mode !== 'REAL' || asset.file_sha256 !== file.sha256) codes.push('PACKAGE_ASSET_MISMATCH');
    }
    for (const doc of proof.documents) {
      if (byteSha256(await readPackageFile(doc.path, root)) !== doc.sha256) codes.push('PACKAGE_DOCUMENT_HASH_MISMATCH');
    }
    for (const [path, sha] of [[proof.render.html_path, proof.render.html_sha256],
      [proof.render.screenshot_path, proof.render.screenshot_sha256], [proof.render.receipt_path, proof.render.receipt_sha256]]) {
      if (!path || !sha || byteSha256(await readPackageFile(path, root)) !== sha) codes.push('PACKAGE_RENDER_HASH_MISMATCH');
    }
    const html = (await readPackageFile(proof.render.html_path, root)).toString('utf8');
    const receipt = JSON.parse((await readPackageFile(proof.render.receipt_path, root)).toString('utf8')) as {
      route: string; browser: string; rendered_at: string; html_sha256: string;
      image: { asset_id: string; usage_id: string; decoded: boolean; natural_width: number; natural_height: number;
        served_sha256: string; caption: string; credit: string; notices: string[]; visible: boolean };
    };
    if (receipt.route !== proof.render.page || !receipt.browser || receipt.html_sha256 !== proof.render.html_sha256
      || !receipt.image?.decoded || !receipt.image.visible) codes.push('PACKAGE_RENDER_NOT_VERIFIED');
    if (html.includes('<script')) codes.push('PACKAGE_UNEXPECTED_CLIENT_SCRIPT');
    for (const id of proof.render.usage_ids) {
      const usage = manifest.usages.find(u => u.id === id), asset = manifest.assets.find(a => a.id === usage?.asset_id);
      const grant = manifest.grants.find(g => g.id === usage?.grant_id);
      if (!usage || !asset || !grant || manifest.decisions.find(d => d.usage_id === id)?.status !== 'ALLOWED'
        || asset.data_mode !== 'REAL' || grant.data_mode !== 'REAL'
        || !proof.documents.some(d => d.path === grant.document.reference && d.sha256 === grant.document.sha256)) {
        codes.push('PACKAGE_USAGE_NOT_AUTHORIZED'); continue;
      }
      if (!html.includes(asset.uri) || !html.includes(id) || !usage.generic_label || !html.includes(usage.generic_label)
        || !usage.attribution_text || !html.includes(usage.attribution_text)) codes.push('PACKAGE_RENDER_BINDING_LOSS');
      if (receipt.image.usage_id !== id || receipt.image.asset_id !== asset.id || receipt.image.served_sha256 !== asset.file_sha256
        || receipt.image.natural_width !== asset.inspection.width || receipt.image.natural_height !== asset.inspection.height
        || receipt.image.caption !== usage.generic_label || receipt.image.credit !== usage.attribution_text
        || grant.required_notices?.some(n => !html.includes(n) || !receipt.image.notices.includes(n))) codes.push('PACKAGE_BROWSER_BINDING_LOSS');
    }
  } catch (error) { codes.push(`PACKAGE_EVIDENCE_INVALID:${String(error)}`); }
  return { success: !codes.length, codes: [...new Set(codes)] };
}
