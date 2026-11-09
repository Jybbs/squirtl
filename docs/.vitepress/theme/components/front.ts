import { StoryLearning } from './front/learning.tsx'
import { StoryRace }     from './front/race.tsx'
import { StoryReward }   from './front/reward.tsx'
import { StorySees }     from './front/sees.tsx'

/**
 * The widgets the front page's story is drawn in, one to each of its parts.
 */
export const FRONT = [StoryLearning, StoryRace, StoryReward, StorySees] as const
