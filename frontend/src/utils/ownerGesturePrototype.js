export const OWNER_GESTURE_RECOGNITION_CONFIG = {
  sampleTarget: 45,
  staticMatchThreshold: 0.7,
  dynamicMatchThreshold: 0.7,
  palmDirectionThreshold: 0.28,
  palmWorldDirectionThreshold: 0.62,
  palmWorldMismatchPenalty: 0.45,
  minDynamicMotion: 0.28,
  staticStillMotionLimit: 0.55,
  staticMotionHardLimit: 0.9,
  staticMotionPenaltyMax: 0.12,
  dynamicMotionRatio: 0.45,
  staticRecognitionHoldMs: 300,
  triggerCooldownMs: 1500,
  defaultHoldMs: 1200,
  sequencePoseWeight: 0.45,
  sequencePathWeight: 0.55,
  motionTrackedIndexes: [[66, 67], [24, 25], [12, 13], [36, 37]],
  vehicleVolumeStep: 8,
  vehicleVolumeMin: 0,
  vehicleVolumeMax: 100,
  vehicleFeatureNames: ['主页', '音乐', '空调', '电话', '导航'],
  defaultVehicleState: {
    power: '待唤醒',
    volume: 35,
    temperature: 24,
    phone: '空闲',
    featureIndex: 0
  }
}

export function extractFeatureVector(landmarks, worldLandmarks) {
  const wrist = landmarks[0]
  const middleBase = landmarks[9]
  const center = landmarks.reduce(
    (acc, point) => ({
      x: acc.x + point.x / landmarks.length,
      y: acc.y + point.y / landmarks.length,
      z: acc.z + (point.z || 0) / landmarks.length
    }),
    { x: 0, y: 0, z: 0 }
  )
  const scale = distance(wrist, middleBase) || 1
  const normalized = landmarks.flatMap(point => [
    (point.x - wrist.x) / scale,
    (point.y - wrist.y) / scale,
    ((point.z || 0) - (wrist.z || 0)) / scale
  ])

  const fingerTips = [4, 8, 12, 16, 20].map(index => landmarks[index])
  const palmSpread = [
    distance(fingerTips[0], fingerTips[4]) / scale,
    distance(fingerTips[1], fingerTips[3]) / scale,
    distance(fingerTips[2], wrist) / scale
  ]

  const palmDirection = palmDirectionScore(landmarks)
  const fingerCurl = [8, 12, 16, 20].map(tipIndex => {
    const pipIndex = tipIndex - 2
    return distance(landmarks[tipIndex], wrist) / (distance(landmarks[pipIndex], wrist) || 1)
  })
  const worldPalmDirection = worldLandmarks ? palmDirectionScore(worldLandmarks) : palmDirection

  return [
    ...normalized,
    ...palmSpread,
    center.x,
    center.y,
    center.z,
    palmDirection,
    ...fingerCurl,
    worldPalmDirection
  ]
}

export function extractLegacyFeatureVector(landmarks) {
  const wrist = landmarks[0]
  const middleBase = landmarks[9]
  const scale = distance(wrist, middleBase) || 1
  return landmarks.flatMap(point => [
    (point.x - wrist.x) / scale,
    (point.y - wrist.y) / scale
  ])
}

export function meanVector(vectors) {
  return vectors[0].map((_, index) => {
    const total = vectors.reduce((sum, vector) => sum + vector[index], 0)
    return total / vectors.length
  })
}

export function recognizePrototype(prototypes, currentVector, currentLegacyVector, sequence, legacySequence, config = OWNER_GESTURE_RECOGNITION_CONFIG) {
  let best = null
  for (const prototype of normalizePrototypes(prototypes, config)) {
    const vector = prototype.vector.length <= 42 ? currentLegacyVector : currentVector
    const liveSequence = prototype.vector.length <= 42 ? legacySequence : sequence
    const result = scorePrototype(prototype, vector, liveSequence, config)
    if (!result.accepted) continue
    if (!best || result.score > best.score) {
      best = { ...prototype, ...result }
    }
  }
  return best
}

export function normalizePrototypes(items, config = OWNER_GESTURE_RECOGNITION_CONFIG) {
  return (items || [])
    .filter(item => item.source === 'custom' || item.kind === 'custom' || item.kind === 'static' || item.kind === 'dynamic')
    .map(item => {
      const vector = numericVector(item.vector || item.prototype)
      const sequence = Array.isArray(item.sequence)
        ? item.sequence.map(numericVector).filter(vector => vector.length)
        : []
      return {
        id: item.id || item.gestureCode,
        gestureCode: item.gestureCode,
        name: item.gestureName || item.name,
        action: item.action,
        kind: item.kind === 'dynamic' ? 'dynamic' : 'static',
        holdMs: Number(item.holdMs || config.defaultHoldMs),
        motion: Number(item.motion || sequenceMotion(sequence, config) || 0),
        vector,
        sequence,
        source: item.source || 'custom'
      }
    })
    .filter(item => item.gestureCode && item.name && item.vector.length)
}

function scorePrototype(prototype, vector, sequence, config) {
  if (!vector?.length || !prototype.vector?.length) {
    return { accepted: false, score: 0, reason: 'empty' }
  }

  if (prototype.kind === 'dynamic' && prototype.sequence?.length) {
    const liveMotion = sequenceMotion(sequence.slice(-config.sampleTarget), config)
    const requiredMotion = Math.max(config.minDynamicMotion, (prototype.motion || 0) * config.dynamicMotionRatio)
    if (liveMotion < requiredMotion) {
      return { accepted: false, score: liveMotion / requiredMotion, reason: 'motion' }
    }
    const score = compareSequence(sequence, prototype.sequence, config)
    return {
      accepted: score >= config.dynamicMatchThreshold,
      score,
      reason: 'dynamic'
    }
  }

  const palmConsistency = palmDirectionConsistency(vector, prototype.vector, config)
  if (palmConsistency < config.palmDirectionThreshold) {
    return { accepted: false, score: palmConsistency, reason: 'palm' }
  }

  let score = cosineSimilarity(vector, prototype.vector)
  const liveMotion = sequenceMotion(sequence.slice(-config.sampleTarget), config)
  if (liveMotion > config.staticStillMotionLimit) {
    const penalty = Math.min(
      (liveMotion - config.staticStillMotionLimit) / config.staticMotionHardLimit,
      config.staticMotionPenaltyMax
    )
    score -= penalty
  }
  return {
    accepted: score >= config.staticMatchThreshold,
    score,
    reason: 'static'
  }
}

export function compareSequence(liveSequence, prototypeSequence, config = OWNER_GESTURE_RECOGNITION_CONFIG) {
  if (!prototypeSequence?.length || liveSequence.length < prototypeSequence.length) {
    return 0
  }

  const window = liveSequence.slice(-prototypeSequence.length)
  const sequenceTotal = prototypeSequence.reduce((sum, prototypeVector, index) => {
    return sum + cosineSimilarity(window[index], prototypeVector)
  }, 0)
  const sequenceScore = sequenceTotal / prototypeSequence.length
  const pathScore = comparePath(window, prototypeSequence, config)
  return sequenceScore * config.sequencePoseWeight + pathScore * config.sequencePathWeight
}

function comparePath(liveSequence, prototypeSequence, config) {
  const livePath = centerDeltas(liveSequence, config)
  const prototypePath = centerDeltas(prototypeSequence, config)
  if (!livePath.length || livePath.length !== prototypePath.length) return 0
  return cosineSimilarity(livePath, prototypePath)
}

function centerDeltas(sequence, config) {
  const values = []
  for (let index = 1; index < sequence.length; index += 1) {
    for (const [xIndex, yIndex] of config.motionTrackedIndexes) {
      if (sequence[index].length <= Math.max(xIndex, yIndex)) continue
      values.push(sequence[index][xIndex] - sequence[index - 1][xIndex])
      values.push(sequence[index][yIndex] - sequence[index - 1][yIndex])
    }
  }
  return values
}

export function sequenceMotion(sequence, config = OWNER_GESTURE_RECOGNITION_CONFIG) {
  if (!sequence?.length || sequence.length < 2) return 0
  let total = 0
  let trackedCount = 0
  for (let index = 1; index < sequence.length; index += 1) {
    let frameMotion = 0
    let frameTracked = 0
    for (const [xIndex, yIndex] of config.motionTrackedIndexes) {
      if (sequence[index].length <= Math.max(xIndex, yIndex)) continue
      frameMotion += Math.hypot(sequence[index][xIndex] - sequence[index - 1][xIndex], sequence[index][yIndex] - sequence[index - 1][yIndex])
      frameTracked += 1
    }
    if (frameTracked) {
      total += frameMotion / frameTracked
      trackedCount += 1
    }
  }
  return trackedCount ? total : 0
}

export function palmDirectionConsistency(currentVector, prototypeVector, config = OWNER_GESTURE_RECOGNITION_CONFIG) {
  if (currentVector.length <= 42 || prototypeVector.length <= 42) return 1

  const currentWorldDirection = palmWorldDirectionFromVector(currentVector)
  const prototypeWorldDirection = palmWorldDirectionFromVector(prototypeVector)
  if (Number.isFinite(currentWorldDirection) && Number.isFinite(prototypeWorldDirection)) {
    const worldConsistency = directionConsistency(currentWorldDirection, prototypeWorldDirection)
    return worldConsistency >= config.palmWorldDirectionThreshold ? worldConsistency : worldConsistency * config.palmWorldMismatchPenalty
  }

  const currentDirection = palmDirectionFromVector(currentVector)
  const prototypeDirection = palmDirectionFromVector(prototypeVector)
  if (!Number.isFinite(currentDirection) || !Number.isFinite(prototypeDirection)) return 1
  return directionConsistency(currentDirection, prototypeDirection)
}

function palmDirectionFromVector(vector) {
  if (vector.length > 69) return vector[69]

  const wrist = vectorPoint(vector, 0)
  const indexBase = vectorPoint(vector, 5)
  const pinkyBase = vectorPoint(vector, 17)
  if (!wrist || !indexBase || !pinkyBase) return Number.NaN

  const indexVector = subtractPoint(indexBase, wrist)
  const pinkyVector = subtractPoint(pinkyBase, wrist)
  const normal = crossProduct(indexVector, pinkyVector)
  const length = Math.hypot(normal.x, normal.y, normal.z) || 1
  return normal.z / length
}

function palmWorldDirectionFromVector(vector) {
  return vector.length > 74 ? vector[74] : Number.NaN
}

function directionConsistency(currentDirection, prototypeDirection) {
  return 1 - Math.min(Math.abs(currentDirection - prototypeDirection), 2) / 2
}

function palmDirectionScore(landmarks) {
  const wrist = landmarks[0]
  const indexBase = landmarks[5]
  const pinkyBase = landmarks[17]
  const indexVector = subtractPoint(indexBase, wrist)
  const pinkyVector = subtractPoint(pinkyBase, wrist)
  const normal = crossProduct(indexVector, pinkyVector)
  const length = Math.hypot(normal.x, normal.y, normal.z) || 1
  return normal.z / length
}

function vectorPoint(vector, landmarkIndex) {
  const start = landmarkIndex * 3
  if (vector.length <= start + 2) return null
  return { x: vector[start], y: vector[start + 1], z: vector[start + 2] }
}

function subtractPoint(a, b) {
  return {
    x: a.x - b.x,
    y: a.y - b.y,
    z: (a.z || 0) - (b.z || 0)
  }
}

function crossProduct(a, b) {
  return {
    x: a.y * b.z - a.z * b.y,
    y: a.z * b.x - a.x * b.z,
    z: a.x * b.y - a.y * b.x
  }
}

export function cosineSimilarity(a, b) {
  if (!a?.length || !b?.length) return 0
  let dot = 0
  let normA = 0
  let normB = 0
  const length = Math.min(a.length, b.length)
  for (let index = 0; index < length; index += 1) {
    dot += a[index] * b[index]
    normA += a[index] * a[index]
    normB += b[index] * b[index]
  }
  return dot / (Math.sqrt(normA) * Math.sqrt(normB) || 1)
}

function distance(a, b) {
  return Math.hypot(a.x - b.x, a.y - b.y, (a.z || 0) - (b.z || 0))
}

function numericVector(value) {
  return Array.isArray(value)
    ? value.map(Number).filter(item => Number.isFinite(item))
    : []
}
