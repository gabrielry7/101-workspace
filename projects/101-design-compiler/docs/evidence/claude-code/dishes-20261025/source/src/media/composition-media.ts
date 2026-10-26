import {tryDishMediaData,evaluateDishUsage} from './dish-media.ts';
import {contextualMediaData,evaluateContextualUsage} from './contextual-review.ts';
import {tryExperienceMediaData,evaluateExperienceUsage} from './experience-review.ts';
import type {ContextualMediaHandle} from './contextual-review.ts';
import {tryRichExperienceMediaData,evaluateRichExperienceUsage} from './rich-experience-review.ts';
export function compositionMedia(handle:ContextualMediaHandle){const dish=tryDishMediaData(handle);if(dish)return {review:dish,evaluate:(u:unknown,at:string)=>evaluateDishUsage(handle,u,at)};const rich=tryRichExperienceMediaData(handle);if(rich)return {review:rich,evaluate:(u:unknown,at:string)=>evaluateRichExperienceUsage(handle,u,at)};const expanded=tryExperienceMediaData(handle);return expanded?{review:expanded,evaluate:(u:unknown,at:string)=>evaluateExperienceUsage(handle,u,at)}:{review:contextualMediaData(handle),evaluate:(u:unknown,at:string)=>evaluateContextualUsage(handle,u,at)};}
