export function createRecognitionEngine(initialPrototypes = [], config) {
  const normalizedConfig = normalizeConfig(config);
  const featureNames = normalizedConfig.vehicleFeatureNames;
  const defaultVehicle = normalizedConfig.defaultVehicleState;

  return {
    config: normalizedConfig,
    prototypes: initialPrototypes,
    liveVectors: [],
    recording: null,
    lastStableName: "",
    stableSince: 0,
    staticStillSince: 0,
    lastTriggerAt: 0,
    vehicle: {
      power: defaultVehicle.power,
      volume: defaultVehicle.volume,
      temperature: defaultVehicle.temperature,
      phone: defaultVehicle.phone,
      featureIndex: defaultVehicle.featureIndex,
      feature: featureNames[defaultVehicle.featureIndex] || featureNames[0]
    }
  };
}

export function updateEngineConfig(engine, nextConfig) {
  engine.config = normalizeConfig(nextConfig);
  engine.liveVectors = engine.liveVectors.slice(-engine.config.sampleTarget);
  engine.staticStillSince = 0;
  engine.lastStableName = "";
  engine.stableSince = 0;
  if (engine.recording) {
    engine.recording.vectors = (engine.recording.vectors || []).slice(-engine.config.sampleTarget);
  }
  return engine.config;
}

export function startRecording(engine, options) {
  if (!["dynamic", "static"].includes(options.kind)) {
    throw new Error("请选择动态或静态手势类型");
  }
  engine.recording = {
    id: cryptoRandomId(),
    name: options.name,
    action: options.action || "NONE",
    kind: options.kind,
    phase: "sampling",
    motion: 0,
    holdMs: Number(options.holdMs || engine.config.defaultHoldMs),
    vectors: []
  };
  return getRecordingStatus(engine);
}

export function cancelRecording(engine) {
  engine.recording = null;
  return getRecordingStatus(engine);
}

export function processFrame(engine, vector, now = performanceNow()) {
  const config = engine.config;
  engine.liveVectors.push(vector);
  if (engine.liveVectors.length > config.sampleTarget) {
    engine.liveVectors.shift();
  }

  const wasRecording = Boolean(engine.recording);
  let recordingComplete = null;
  if (engine.recording) {
    recordingComplete = processRecordingFrame(engine, vector);
  }

  const liveMotion = sequenceMotion(engine.liveVectors.slice(-config.sampleTarget), config);
  const staticReady = updateStaticReadiness(engine, liveMotion, now);
  let recognition;
  if (wasRecording) {
    recognition = createRecordingRecognition(engine, recordingComplete, liveMotion);
  } else {
    const match = matchPrototype(engine.prototypes, vector, engine.liveVectors, staticReady, config);
    recognition = match
      ? handleStableTrigger(engine, match, now)
      : createRejectedRecognition(engine, liveMotion, staticReady, now);
  }

  return {
    recognition,
    recording: getRecordingStatus(engine),
    recordingComplete,
    prototypes: summarizePrototypes(engine.prototypes),
    vehicle: getVehicleState(engine),
    config
  };
}

export function recognizeOnce(prototypes, vector, sequence = [], config, now = performanceNow()) {
  const tempEngine = createRecognitionEngine(prototypes, config);
  tempEngine.liveVectors = sequence.length ? sequence.slice(-tempEngine.config.sampleTarget) : [vector];
  tempEngine.staticStillSince = now - tempEngine.config.staticRecognitionHoldMs;
  const liveMotion = sequenceMotion(tempEngine.liveVectors, tempEngine.config);
  const match = matchPrototype(prototypes, vector, tempEngine.liveVectors, true, tempEngine.config);
  return match
    ? {
        accepted: true,
        id: match.id,
        gestureCode: match.id,
        name: match.name,
        action: match.action,
        kind: normalizePrototypeKind(match),
        score: match.score,
        motion: liveMotion,
        motionLabel: motionLabel(liveMotion, tempEngine.config)
      }
    : { accepted: false, name: "unknown", score: 0, motion: liveMotion, motionLabel: motionLabel(liveMotion, tempEngine.config) };
}

export function deletePrototype(engine, id) {
  engine.prototypes = engine.prototypes.filter((prototype) => prototype.id !== id);
  return engine.prototypes;
}

export function clearPrototypes(engine) {
  engine.prototypes = [];
  engine.lastStableName = "";
  engine.stableSince = 0;
  return engine.prototypes;
}

export function getRecordingStatus(engine) {
  if (!engine.recording) {
    return {
      active: false,
      kind: "static",
      phase: "idle",
      count: 0,
      target: engine.config.sampleTarget,
      detectCount: 0,
      detectTarget: 0,
      sampleCount: 0,
      sampleTarget: engine.config.sampleTarget,
      totalCount: 0,
      totalTarget: engine.config.sampleTarget,
      motion: 0,
      motionLabel: motionLabel(0, engine.config)
    };
  }

  const sampleCount = (engine.recording.vectors || []).length;
  const phase = engine.recording.phase || "sampling";
  return {
    active: true,
    id: engine.recording.id,
    name: engine.recording.name,
    kind: engine.recording.kind,
    phase,
    count: sampleCount,
    target: engine.config.sampleTarget,
    detectCount: 0,
    detectTarget: 0,
    sampleCount,
    sampleTarget: engine.config.sampleTarget,
    totalCount: sampleCount,
    totalTarget: engine.config.sampleTarget,
    motion: engine.recording.motion || 0,
    motionLabel: motionLabel(engine.recording.motion || 0, engine.config)
  };
}

export function getVehicleState(engine) {
  return { ...engine.vehicle };
}

export function summarizePrototypes(prototypes) {
  return prototypes.map((prototype) => ({
    id: prototype.id,
    name: prototype.name,
    action: prototype.action,
    kind: normalizePrototypeKind(prototype),
    holdMs: prototype.holdMs,
    motion: prototype.motion || 0,
    createdAt: prototype.createdAt
  }));
}

function finishRecording(engine) {
  const recording = engine.recording;
  const vector = meanVector(recording.vectors);
  const motion = sequenceMotion(recording.vectors, engine.config);
  const prototype = {
    id: cryptoRandomId(),
    name: recording.name,
    action: recording.action,
    kind: recording.kind,
    holdMs: recording.holdMs,
    motion,
    vector,
    sequence: recording.vectors,
    createdAt: new Date().toISOString()
  };

  engine.prototypes = [prototype, ...engine.prototypes.filter((item) => item.name !== prototype.name)];
  engine.recording = null;
  return summarizePrototypes([prototype])[0];
}

function processRecordingFrame(engine, vector) {
  const recording = engine.recording;
  const config = engine.config;

  recording.vectors ||= [];

  recording.phase = "sampling";
  recording.vectors.push(vector);
  if (recording.vectors.length >= config.sampleTarget) {
    return finishRecording(engine);
  }
  return null;
}

function createRecordingRecognition(engine, recordingComplete, liveMotion) {
  if (recordingComplete) {
    return {
      accepted: false,
      name: recordingComplete.name,
      kind: recordingComplete.kind,
      score: null,
      motion: liveMotion,
      motionLabel: motionLabel(liveMotion, engine.config),
      triggerState: `录入完成：${kindLabel(recordingComplete.kind)}`
    };
  }

  const recording = engine.recording || {};
  const triggerState = recording ? `${kindLabel(recording.kind)}采样中` : "录入中";
  return {
    accepted: false,
    name: recording.name || "录入中",
    kind: recording.kind || "pending",
    score: null,
    motion: liveMotion,
    motionLabel: motionLabel(liveMotion, engine.config),
    triggerState
  };
}

function matchPrototype(prototypes, vector, sequence, staticReady, config) {
  let best = null;
  for (const prototype of prototypes) {
    const result = scorePrototype(prototype, vector, sequence, staticReady, config);
    if (!result.accepted) continue;
    if (!best || result.score > best.score) {
      best = { ...prototype, ...result };
    }
  }
  return best;
}

function scorePrototype(prototype, vector, sequence, staticReady, config) {
  const kind = normalizePrototypeKind(prototype);
  const liveMotion = sequenceMotion(sequence.slice(-config.sampleTarget), config);

  if (kind === "dynamic") {
    const requiredMotion = Math.max(config.minDynamicMotion, (prototype.motion || 0) * config.dynamicMotionRatio);
    if (liveMotion < requiredMotion) {
      return { accepted: false, score: liveMotion / requiredMotion, reason: "motion" };
    }

    const score = compareSequence(sequence, prototype.sequence, config);
    return {
      accepted: score >= config.dynamicMatchThreshold,
      score,
      reason: "dynamic"
    };
  }

  if (!staticReady) {
    return { accepted: false, score: 0, reason: "static-hold" };
  }

  const palmConsistency = palmDirectionConsistency(vector, prototype.vector, config);
  if (palmConsistency < config.palmDirectionThreshold) {
    return { accepted: false, score: palmConsistency, reason: "palm" };
  }

  let score = cosineSimilarity(vector, prototype.vector);
  if (liveMotion > config.staticStillMotionLimit) {
    const penalty = Math.min(
      (liveMotion - config.staticStillMotionLimit) / config.staticMotionHardLimit,
      config.staticMotionPenaltyMax
    );
    score -= penalty;
  }

  return {
    accepted: score >= config.staticMatchThreshold,
    score,
    reason: "static"
  };
}

function updateStaticReadiness(engine, motion, now) {
  const config = engine.config;
  if (motion <= config.staticStillMotionLimit) {
    engine.staticStillSince ||= now;
  } else {
    engine.staticStillSince = 0;
  }

  return Boolean(engine.staticStillSince && now - engine.staticStillSince >= config.staticRecognitionHoldMs);
}

function createRejectedRecognition(engine, liveMotion, staticReady, now) {
  engine.lastStableName = "";
  engine.stableSince = 0;
  return {
    accepted: false,
    name: engine.prototypes.length ? "unknown" : "未录入",
    score: null,
    motion: liveMotion,
    motionLabel: motionLabel(liveMotion, engine.config),
    triggerState: staticHoldMessage(engine, liveMotion, staticReady, now) || (engine.prototypes.length ? "拒识" : "等待录入")
  };
}

function handleStableTrigger(engine, match, now) {
  const config = engine.config;
  if (match.name === engine.lastStableName) {
    engine.stableSince ||= now;
  } else {
    engine.lastStableName = match.name;
    engine.stableSince = now;
  }

  const holdMs = match.holdMs || config.defaultHoldMs;
  const elapsed = now - engine.stableSince;
  const remaining = Math.max(holdMs - elapsed, 0);
  let triggered = false;

  if (elapsed >= holdMs && now - engine.lastTriggerAt > config.triggerCooldownMs) {
    engine.lastTriggerAt = now;
    triggered = true;
    applyVehicleAction(engine, match.action);
  }

  const liveMotion = sequenceMotion(engine.liveVectors.slice(-config.sampleTarget), config);
  return {
    accepted: true,
    id: match.id,
    gestureCode: match.id,
    name: match.name,
    action: match.action,
    kind: normalizePrototypeKind(match),
    score: match.score,
    motion: liveMotion,
    motionLabel: motionLabel(liveMotion, config),
    triggerState: triggered ? "已触发" : remaining ? `稳定中 ${Math.ceil(remaining / 100) / 10}s` : "可触发",
    triggered
  };
}

function applyVehicleAction(engine, action) {
  const config = engine.config;
  const featureNames = config.vehicleFeatureNames;
  switch (action) {
    case "wake":
      engine.vehicle.power = "已唤醒";
      break;
    case "confirm":
      engine.vehicle.power = "已执行";
      break;
    case "volume_up":
      engine.vehicle.volume = Math.min(engine.vehicle.volume + config.vehicleVolumeStep, config.vehicleVolumeMax);
      break;
    case "volume_down":
      engine.vehicle.volume = Math.max(engine.vehicle.volume - config.vehicleVolumeStep, config.vehicleVolumeMin);
      break;
    case "next_feature":
      engine.vehicle.featureIndex = (engine.vehicle.featureIndex + 1) % featureNames.length;
      engine.vehicle.feature = featureNames[engine.vehicle.featureIndex];
      break;
    case "answer_call":
      engine.vehicle.phone = "通话中";
      break;
    case "hangup_call":
      engine.vehicle.phone = "已挂断";
      break;
    case "home":
      engine.vehicle.featureIndex = 0;
      engine.vehicle.feature = featureNames[0];
      break;
    default:
      break;
  }
}

function staticHoldMessage(engine, motion, staticReady, now) {
  const config = engine.config;
  if (staticReady || motion > config.staticStillMotionLimit || !hasStaticPrototype(engine)) return "";
  const elapsed = now - engine.staticStillSince;
  const remaining = Math.max(config.staticRecognitionHoldMs - elapsed, 0);
  return `静态稳定中 ${Math.ceil(remaining / 100) / 10}s`;
}

function hasStaticPrototype(engine) {
  return engine.prototypes.some((prototype) => normalizePrototypeKind(prototype) === "static");
}

export function extractFeatureVector(landmarks, worldLandmarks) {
  const wrist = landmarks[0];
  const middleBase = landmarks[9];
  const center = landmarks.reduce(
    (acc, point) => ({
      x: acc.x + point.x / landmarks.length,
      y: acc.y + point.y / landmarks.length,
      z: acc.z + (point.z || 0) / landmarks.length
    }),
    { x: 0, y: 0, z: 0 }
  );
  const scale = distance(wrist, middleBase) || 1;
  const normalized = landmarks.flatMap((point) => [
    (point.x - wrist.x) / scale,
    (point.y - wrist.y) / scale,
    (point.z - wrist.z) / scale
  ]);

  const fingerTips = [4, 8, 12, 16, 20].map((index) => landmarks[index]);
  const palmSpread = [
    distance(fingerTips[0], fingerTips[4]) / scale,
    distance(fingerTips[1], fingerTips[3]) / scale,
    distance(fingerTips[2], wrist) / scale
  ];

  const palmDirection = palmDirectionScore(landmarks);
  const fingerCurl = [8, 12, 16, 20].map((tipIndex) => {
    const pipIndex = tipIndex - 2;
    return distance(landmarks[tipIndex], wrist) / (distance(landmarks[pipIndex], wrist) || 1);
  });
  const worldPalmDirection = worldLandmarks ? palmDirectionScore(worldLandmarks) : palmDirection;

  return [
    ...normalized,
    ...palmSpread,
    center.x,
    center.y,
    center.z,
    palmDirection,
    ...fingerCurl,
    worldPalmDirection
  ];
}

export function meanVector(vectors) {
  return vectors[0].map((_, index) => {
    const total = vectors.reduce((sum, vector) => sum + vector[index], 0);
    return total / vectors.length;
  });
}

export function compareSequence(liveSequence, prototypeSequence, config) {
  if (!prototypeSequence?.length || liveSequence.length < prototypeSequence.length) {
    return 0;
  }

  const window = liveSequence.slice(-prototypeSequence.length);
  const sequenceTotal = prototypeSequence.reduce((sum, prototypeVector, index) => {
    return sum + cosineSimilarity(window[index], prototypeVector);
  }, 0);
  const sequenceScore = sequenceTotal / prototypeSequence.length;
  const pathScore = comparePath(window, prototypeSequence, config);
  return sequenceScore * config.sequencePoseWeight + pathScore * config.sequencePathWeight;
}

function comparePath(liveSequence, prototypeSequence, config) {
  const livePath = centerDeltas(liveSequence, config);
  const prototypePath = centerDeltas(prototypeSequence, config);
  if (!livePath.length || livePath.length !== prototypePath.length) return 0;
  return cosineSimilarity(livePath, prototypePath);
}

function centerDeltas(sequence, config) {
  const values = [];
  for (let index = 1; index < sequence.length; index += 1) {
    for (const [xIndex, yIndex] of config.motionTrackedIndexes) {
      values.push(sequence[index][xIndex] - sequence[index - 1][xIndex]);
      values.push(sequence[index][yIndex] - sequence[index - 1][yIndex]);
    }
  }
  return values;
}

export function sequenceMotion(sequence, config) {
  if (!sequence?.length || sequence.length < 2) return 0;
  let total = 0;
  for (let index = 1; index < sequence.length; index += 1) {
    let frameMotion = 0;
    for (const [xIndex, yIndex] of config.motionTrackedIndexes) {
      frameMotion += Math.hypot(sequence[index][xIndex] - sequence[index - 1][xIndex], sequence[index][yIndex] - sequence[index - 1][yIndex]);
    }
    total += frameMotion / config.motionTrackedIndexes.length;
  }
  return total;
}

export function normalizePrototypeKind(prototype) {
  return prototype.kind === "dynamic" ? "dynamic" : "static";
}

export function palmDirectionConsistency(currentVector, prototypeVector, config) {
  const currentWorldDirection = palmWorldDirectionFromVector(currentVector);
  const prototypeWorldDirection = palmWorldDirectionFromVector(prototypeVector);
  if (Number.isFinite(currentWorldDirection) && Number.isFinite(prototypeWorldDirection)) {
    const worldConsistency = directionConsistency(currentWorldDirection, prototypeWorldDirection);
    return worldConsistency >= config.palmWorldDirectionThreshold ? worldConsistency : worldConsistency * config.palmWorldMismatchPenalty;
  }

  const currentDirection = palmDirectionFromVector(currentVector);
  const prototypeDirection = palmDirectionFromVector(prototypeVector);
  if (!Number.isFinite(currentDirection) || !Number.isFinite(prototypeDirection)) return 1;
  return directionConsistency(currentDirection, prototypeDirection);
}

function palmDirectionFromVector(vector) {
  if (vector.length > 69) return vector[69];

  const wrist = vectorPoint(vector, 0);
  const indexBase = vectorPoint(vector, 5);
  const pinkyBase = vectorPoint(vector, 17);
  if (!wrist || !indexBase || !pinkyBase) return Number.NaN;

  const indexVector = subtractPoint(indexBase, wrist);
  const pinkyVector = subtractPoint(pinkyBase, wrist);
  const normal = crossProduct(indexVector, pinkyVector);
  const length = Math.hypot(normal.x, normal.y, normal.z) || 1;
  return normal.z / length;
}

function palmWorldDirectionFromVector(vector) {
  return vector.length > 74 ? vector[74] : Number.NaN;
}

function directionConsistency(currentDirection, prototypeDirection) {
  return 1 - Math.min(Math.abs(currentDirection - prototypeDirection), 2) / 2;
}

function palmDirectionScore(landmarks) {
  const wrist = landmarks[0];
  const indexBase = landmarks[5];
  const pinkyBase = landmarks[17];
  const indexVector = subtractPoint(indexBase, wrist);
  const pinkyVector = subtractPoint(pinkyBase, wrist);
  const normal = crossProduct(indexVector, pinkyVector);
  const length = Math.hypot(normal.x, normal.y, normal.z) || 1;
  return normal.z / length;
}

function vectorPoint(vector, landmarkIndex) {
  const start = landmarkIndex * 3;
  if (vector.length <= start + 2) return null;
  return { x: vector[start], y: vector[start + 1], z: vector[start + 2] };
}

function subtractPoint(a, b) {
  return {
    x: a.x - b.x,
    y: a.y - b.y,
    z: (a.z || 0) - (b.z || 0)
  };
}

function crossProduct(a, b) {
  return {
    x: a.y * b.z - a.z * b.y,
    y: a.z * b.x - a.x * b.z,
    z: a.x * b.y - a.y * b.x
  };
}

export function cosineSimilarity(a, b) {
  if (!a?.length || !b?.length) return 0;
  let dot = 0;
  let normA = 0;
  let normB = 0;
  const length = Math.min(a.length, b.length);
  for (let i = 0; i < length; i += 1) {
    dot += a[i] * b[i];
    normA += a[i] * a[i];
    normB += b[i] * b[i];
  }
  return dot / (Math.sqrt(normA) * Math.sqrt(normB) || 1);
}

function distance(a, b) {
  return Math.hypot(a.x - b.x, a.y - b.y, (a.z || 0) - (b.z || 0));
}

export function motionLabel(motion, config) {
  const value = motion.toFixed(2);
  if (motion <= config.minDynamicMotion) return `画面静态 ${value}`;
  if (motion <= config.staticStillMotionLimit) return `画面小幅变化 ${value}`;
  return `画面动态 ${value}`;
}

function inferKindFromMotion(motion, config) {
  return motion >= config.minDynamicMotion ? "dynamic" : "static";
}

function kindLabel(kind) {
  return kind === "dynamic" ? "动态轨迹" : "静态姿态";
}

function normalizeConfig(config) {
  return JSON.parse(JSON.stringify(config));
}

function cryptoRandomId() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}

function performanceNow() {
  return globalThis.performance?.now ? globalThis.performance.now() : Date.now();
}
