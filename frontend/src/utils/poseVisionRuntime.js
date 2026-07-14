import { FilesetResolver } from '@/vendor/tasks-vision/vision_bundle.mjs'

let visionFilesetPromise

export function getPoseVisionFileset() {
  visionFilesetPromise ||= FilesetResolver.forVisionTasks('/wasm')
  return visionFilesetPromise
}
