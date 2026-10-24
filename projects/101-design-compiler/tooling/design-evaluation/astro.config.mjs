import base from '../../astro.config.mjs';
import designEvaluationPreview from './compiler-extension.mjs';
// Opt-in extension of the actual compiler config; no settings/renderer duplicated.
process.env.DESIGN_EVALUATION_PREVIEW='1';
export default {...base,root:process.cwd(),integrations:[...(base.integrations??[]),designEvaluationPreview()]};
