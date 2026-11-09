import { MethodsCurriculum } from './methods/curriculum.tsx'
import { MethodsDiscount }   from './methods/discount.tsx'
import { MethodsExperience } from './methods/experience.tsx'
import { MethodsMemory }     from './methods/memory.tsx'
import { MethodsReach }      from './methods/reach.tsx'
import { MethodsStep }       from './methods/step.tsx'

/**
 * The widgets a page of the Methods section closes a part on.
 */
export const METHODS = [MethodsCurriculum, MethodsDiscount, MethodsExperience, MethodsMemory, MethodsReach, MethodsStep] as const
