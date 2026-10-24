import {z} from 'zod';
const sha=z.string().regex(/^[a-f0-9]{64}$/);
export const experiencePages=[
 {kind:'home',slug:'',label:'Inicio'}, {kind:'collection',slug:'carta',label:'La carta'},
 {kind:'request',slug:'reservas',label:'Reservas'}, {kind:'selection',slug:'pedidos',label:'Pedidos'},
 {kind:'visit',slug:'visita',label:'La visita'}, {kind:'story',slug:'historia',label:'Nuestra idea'},
 {kind:'faq',slug:'preguntas',label:'Preguntas'}, {kind:'credits',slug:'creditos',label:'Créditos'},
] as const;
export const ExperienceV1=z.strictObject({schema_version:z.literal('1.0.0'),kind:z.literal('B3_MULTIPAGE_EXPERIENCE'),
 source_context_sha256:sha,content_sha256:sha,plan_sha256:sha,media_review_sha256:sha,research_sha256:sha,
 feedback_status:z.literal('HUMAN_REQUESTED_ITERATION_NO_SCORE'),human_approval:z.literal('NOT_COLLECTED'),
 profiles:z.array(z.strictObject({id:z.string().regex(/^candidate-0[1-4]$/),label:z.string().min(1),
  root:z.string().regex(/^\/b3\/candidate-0[1-4]\/$/),hero:z.enum(['Immersive','Masthead','Cinema','EditorialFilm']),
  palette:z.enum(['WhiteInk','Vermilion','Nocturne','PureWhite']),type:z.enum(['Classic','Condensed','Italic','Modern']),
  collection:z.enum(['Spread','Rows','Exhibit','Index']),rationale:z.string().min(40),references:z.array(z.string().regex(/^reference-\d{2}$/)).min(1),
 })).length(4),
});
export type Experience=z.infer<typeof ExperienceV1>;
export type ExperiencePage=typeof experiencePages[number];
export function experienceRoute(root:string,page:ExperiencePage){return root+(page.slug?`${page.slug}/`:'');}
