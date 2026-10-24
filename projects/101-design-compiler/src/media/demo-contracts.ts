import {z} from 'zod';
import {MediaAssetV1,LicenseGrantV1,MediaUsageV1} from './contracts.ts';
const sha=z.string().regex(/^[a-f0-9]{64}$/),text=z.string().min(1);
const file=z.strictObject({path:text,sha256:sha,bytes:z.number().int().positive()});
export const FictionalMediaPackageV1=z.strictObject({schema_version:z.literal('1.0.0'),kind:z.literal('FICTIONAL_MEDIA_PACKAGE'),package_sha256:sha,
 scenario:z.strictObject({id:text,title:text,mode:z.literal('SYNTHETIC_DEMO'),business_id:text,site_plan_sha256:sha,input_sha256:sha,client_id:text,project_id:text,scope_id:text,real_business_evidence:z.literal(false)}),
 evaluated_at:z.iso.datetime(),needs:z.array(z.strictObject({id:text,label:text,placement:z.enum(['CARD','MOTION','POSTER']),scope_id:text,purpose:text,role:z.enum(['ILLUSTRATIVE','ATMOSPHERIC']),target_module:text,target_capability:text,target_feature:text,source_need_ids:z.array(text),satisfies_documentary_need:z.literal(false)})),
 assets:z.array(MediaAssetV1),grants:z.array(LicenseGrantV1),usages:z.array(MediaUsageV1),files:z.array(file.extend({asset_id:text,publication:z.enum(['PRIVATE_SOURCE','LOCAL_COMPOSITE_ONLY'])})),
 sources:z.array(z.strictObject({asset_id:text,provider_id:z.number().int(),page:z.url(),contributor:text,published_date:text,license:z.enum(['PIXABAY_CONTENT_LICENSE','CC0_1_0_BY_TERMS_SECTION_4']),terms_version:z.literal('2024-11-18'),camera_original:z.literal('NOT_OBTAINED'),ai_generated:z.literal('NOT_REPORTED')})),
 evidence:z.array(file),silent_video:z.strictObject({source_asset_id:text,render_asset_id:text,source_sha256:sha,render_sha256:sha,method:z.literal('PIXEL_ONLY_TRANSCODE'),receipt_path:text,source_audio:z.literal('PRESENT'),render_audio:z.literal('NONE')}),
 human_aesthetic_approval:z.literal('NOT_COLLECTED'),public_stock_redistribution:z.literal(false)});
export type FictionalMediaPackage=z.infer<typeof FictionalMediaPackageV1>;
