import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {resolve, relative, isAbsolute} from 'node:path';
import sharp from 'sharp';

// Read-only replay of research evidence, not a browser audit or a taste score.
const root = process.cwd();
const digest = (bytes: Uint8Array) => createHash('sha256').update(bytes).digest('hex');
const read = async (path: string) => {
  const absolute = resolve(root, path), rel = relative(root, absolute);
  if (rel.startsWith('..') || isAbsolute(rel)) throw Error('REFERENCE_PATH_OUTSIDE_WORKSPACE');
  return readFile(absolute);
};
const corpusBytes = await read('data/reference/design/corpus-v1.json');
const corpus = JSON.parse(corpusBytes.toString('utf8'));
const review = JSON.parse((await read('data/reference/design/visual-review-2026-10-15.json')).toString('utf8'));
const same = (a: unknown,b: unknown) => JSON.stringify(a) === JSON.stringify(b);
if (review.kind !== 'ASSISTANT_VISUAL_REFERENCE_REVIEW' || review.status !== 'REPRESENTATIVE_VIEWS_REVIEWED_WITH_LIMITS'
  || review.authority !== 'ASSISTANT_OBSERVATIONS_NOT_NEW_USER_VOTES'
  || review.source_corpus_bytes_sha256 !== digest(corpusBytes)
  || review.source_corpus_semantic_sha256 !== corpus.corpus_sha256
  || review.source_document_path !== corpus.source_path
  || review.source_document_bytes_sha256 !== digest(await read(corpus.source_path))
  || review.user_approval_of_generated_designs !== 'NOT_COLLECTED' || review.training !== 'NOT_PERFORMED'
  || review.external_assets_reused !== false
  || review.runtime_consumption !== 'ASSOCIATED_RESEARCH_INPUT_NOT_IN_ACTIVE_PRODUCER_CONTEXT'
  || review.coverage.references !== 21 || review.coverage.representative_views !== 42
  || review.coverage.all_subpages_audited !== false || review.coverage.all_videos_quality_verified !== false
  || review.coverage.accessibility_certified !== false || review.coverage.network_performance_audited !== false
  || review.references.length !== corpus.references.length) throw Error('REFERENCE_REVIEW_AUTHORITY_OR_COVERAGE_CHANGED');
const ledger = JSON.parse((await read('docs/evidence/corrections/b3/external-references-2026-10-15/capture-ledger.json')).toString('utf8'));
const ids = new Set<string>(), paths = new Set<string>();
let views = 0;
for (const ref of review.references) {
  const original = corpus.references.find((r: any) => r.id === ref.id);
  if (!original || ids.has(ref.id) || ref.url !== original.url || ref.approved_scope !== original.approved_scope
    || ref.reported_intensity_literal !== original.reported_intensity_literal
    || !same(ref.prior_negative_or_limit_lines, original.negative_or_limit_lines)
    || ref.new_user_vote !== null || ref.asset_reuse !== 'NOT_AUTHORIZED_BY_REFERENCE'
    || ref.proposal_status !== 'RESEARCH_PROPOSAL_NOT_IMPLEMENTED' || ref.status !== 'OBSERVED_WITH_LIMITS'
    || !ref.limitations || !ref.proposed_shared_rule
    || ['composition','typography','palette_and_media','mobile'].some(k => typeof ref.observations[k] !== 'string' || !ref.observations[k])) throw Error('REFERENCE_SCOPE_OR_OBSERVATION_INVALID');
  ids.add(ref.id);
  if (ref.captures.length !== 2 || !same(ref.captures.map((c:any)=>c.view).sort(), ['desktop','mobile'])) throw Error('REFERENCE_VIEW_MISSING');
  for (const capture of ref.captures) {
    const source = ledger.receipts.find((c:any)=>c.reference_id===ref.id && c.view===capture.view && c.screenshot.path===capture.capture);
    const expected = capture.view === 'desktop' ? {width:1440,height:1000} : {width:390,height:844};
    const url = new URL(capture.url), originalUrl = new URL(original.url);
    if (!source || !source.valid_url || !source.valid_image_width || !source.valid_viewport
      || url.hostname.replace(/^www\./,'') !== originalUrl.hostname.replace(/^www\./,'')
      || (ref.approved_scope === 'SPECIFIC_PAGE_ONLY' && url.pathname !== originalUrl.pathname)
      || !same(capture.viewport,expected) || paths.has(capture.capture)
      || capture.capture_sha256 !== source.screenshot.sha256 || capture.captured_at !== source.captured_at) throw Error('REFERENCE_CAPTURE_BINDING_INVALID');
    const bytes = await read(capture.capture), metadata = await sharp(bytes).metadata();
    if (digest(bytes) !== capture.capture_sha256 || metadata.width !== capture.pixel.width || metadata.height !== capture.pixel.height
      || (metadata.format === 'jpeg' ? 'jpg' : metadata.format) !== capture.pixel.format) throw Error('REFERENCE_CAPTURE_BYTES_CHANGED');
    paths.add(capture.capture); views++;
  }
}
for (const supplement of review.supplements) {
  const bytes = await read(supplement.path), metadata = await sharp(bytes).metadata();
  if (digest(bytes) !== supplement.sha256 || metadata.width !== supplement.pixel.width || metadata.height !== supplement.pixel.height) throw Error('REFERENCE_SUPPLEMENT_CHANGED');
}
console.log(JSON.stringify({status:'PASS_REFERENCE_EVIDENCE_REPLAY',references:ids.size,representative_views:views,
  new_user_votes:0,source_corpus:'UNCHANGED_BY_REVIEW',active_producer_context:'UNCHANGED_BY_REVIEW',
  limitation:'Representative visual observations with per-reference limits; not full site/media/accessibility certification or B3 approval.'}));
