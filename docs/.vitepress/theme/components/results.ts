import { ResultsComparison } from './results/comparison.tsx'
import { ResultsCurves }     from './results/curves.tsx'

/**
 * The widgets a page of the Results section closes a part on.
 */
export const RESULTS = [ResultsComparison, ResultsCurves] as const
