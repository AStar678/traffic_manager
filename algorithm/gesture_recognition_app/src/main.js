import { DrawingUtils, FilesetResolver, GestureRecognizer } from "@mediapipe/tasks-vision";
import { extractFeatureVector } from "./gesture-engine.js";
import "./styles.css";

const MODEL_PATH = "/models/gesture_recognizer.task";

const els = {
  modelStatus: document.querySelector("#modelStatus"),
  webcam: document.querySelector("#webcam"),
  countdownWebcam: document.querySelector("#countdownWebcam"),
  countdownScreen: document.querySelector("#countdownScreen"),
  countdownValue: document.querySelector("#countdownValue"),
  overlay: document.querySelector("#overlay"),
  cameraEmpty: document.querySelector("#cameraEmpty"),
  startCameraBtn: document.querySelector("#startCameraBtn"),
  stopCameraBtn: document.querySelector("#stopCameraBtn"),
  clearStorageBtn: document.querySelector("#clearStorageBtn"),
  builtinGesture: document.querySelector("#builtinGesture"),
  prototypeMatch: document.querySelector("#prototypeMatch"),
  similarityScore: document.querySelector("#similarityScore"),
  triggerState: document.querySelector("#triggerState"),
  gestureNameInput: document.querySelector("#gestureNameInput"),
  actionSelect: document.querySelector("#actionSelect"),
  gestureKindSelect: document.querySelector("#gestureKindSelect"),
  holdMsSelect: document.querySelector("#holdMsSelect"),
  recordBtn: document.querySelector("#recordBtn"),
  cancelRecordBtn: document.querySelector("#cancelRecordBtn"),
  recordHint: document.querySelector("#recordHint"),
  sampleCount: document.querySelector("#sampleCount"),
  prototypeCount: document.querySelector("#prototypeCount"),
  prototypeList: document.querySelector("#prototypeList"),
  vehiclePower: document.querySelector("#vehiclePower"),
  volumeSlider: document.querySelector("#volumeSlider"),
  tempSlider: document.querySelector("#tempSlider"),
  phoneState: document.querySelector("#phoneState"),
  featureState: document.querySelector("#featureState")
};

const ctx = els.overlay.getContext("2d");
const drawingUtils = new DrawingUtils(ctx);

let recognizer;
let mediaStream;
let animationFrame;
let lastVideoTime = -1;
let prototypes = [];
let isRecording = false;
let isCountdownOpen = false;
let recognitionSocket;
let serviceConfig;
let countdownTimer;

init();

async function init() {
  await loadServiceState();
  connectRecognitionStream();

  try {
    const vision = await FilesetResolver.forVisionTasks("/wasm");
    recognizer = await createRecognizer(vision);
    els.modelStatus.textContent = "模型已就绪";
    els.modelStatus.classList.add("ready");
    updateRecordButton();
  } catch (error) {
    console.error(error);
    els.modelStatus.textContent = "模型加载失败";
    els.modelStatus.classList.add("error");
    els.recordHint.textContent = "请确认已安装依赖并通过本地服务器访问页面。";
  }
}

els.startCameraBtn.addEventListener("click", startCamera);
els.stopCameraBtn.addEventListener("click", stopCamera);
els.recordBtn.addEventListener("click", startCountdownRecording);
els.cancelRecordBtn.addEventListener("click", () => stopRecording());
els.clearStorageBtn.addEventListener("click", clearPrototypes);

async function loadServiceState() {
  try {
    applyServiceState(await apiRequest("/api/state"));
  } catch (error) {
    console.error(error);
    renderPrototypes();
    els.triggerState.textContent = "识别服务未连接";
    els.recordHint.textContent = recordingHint();
  }
}

function connectRecognitionStream() {
  const protocol = location.protocol === "https:" ? "wss:" : "ws:";
  recognitionSocket = new WebSocket(`${protocol}//${location.host}/api/recognition/stream`);

  recognitionSocket.addEventListener("open", () => {
    els.triggerState.textContent = "识别服务已连接";
  });

  recognitionSocket.addEventListener("message", (event) => {
    try {
      applyServiceState(JSON.parse(event.data));
    } catch (error) {
      console.error(error);
    }
  });

  recognitionSocket.addEventListener("close", () => {
    els.triggerState.textContent = "识别服务重连中";
    window.setTimeout(connectRecognitionStream, 1000);
  });
}

async function startCamera() {
  if (mediaStream) return true;
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "user" },
      audio: false
    });
    els.webcam.srcObject = mediaStream;
    if (els.countdownWebcam) {
      els.countdownWebcam.srcObject = mediaStream;
    }
    await els.webcam.play();
    resizeCanvas();
    els.cameraEmpty.hidden = true;
    els.startCameraBtn.disabled = true;
    els.stopCameraBtn.disabled = false;
    updateRecordButton();
    predictLoop();
    return true;
  } catch (error) {
    console.error(error);
    els.recordHint.textContent = "摄像头启动失败：请在浏览器里允许摄像头权限。";
    return false;
  }
}

function stopCamera() {
  cancelAnimationFrame(animationFrame);
  animationFrame = undefined;
  window.clearInterval(countdownTimer);
  isCountdownOpen = false;
  if (els.countdownScreen) {
    els.countdownScreen.hidden = true;
  }
  mediaStream?.getTracks().forEach((track) => track.stop());
  mediaStream = undefined;
  els.webcam.srcObject = null;
  if (els.countdownWebcam) {
    els.countdownWebcam.srcObject = null;
  }
  ctx.clearRect(0, 0, els.overlay.width, els.overlay.height);
  els.cameraEmpty.hidden = false;
  els.startCameraBtn.disabled = false;
  els.stopCameraBtn.disabled = true;
  updateRecordButton();
  if (isRecording) {
    void stopRecording({ keepHint: true });
  }
}

function predictLoop() {
  if (!recognizer || !mediaStream) return;

  if (els.webcam.videoWidth && els.webcam.videoHeight) {
    resizeCanvas();
  }

  if (els.webcam.currentTime !== lastVideoTime) {
    lastVideoTime = els.webcam.currentTime;
    const result = recognizer.recognizeForVideo(els.webcam, performance.now());
    drawResult(result);
    updateRecognition(result);
  }

  animationFrame = requestAnimationFrame(predictLoop);
}

function drawResult(result) {
  ctx.clearRect(0, 0, els.overlay.width, els.overlay.height);
  const landmarks = result.landmarks?.[0];
  if (!landmarks) return;

  drawingUtils.drawConnectors(landmarks, GestureRecognizer.HAND_CONNECTIONS, {
    color: "#2f6f6b",
    lineWidth: 3
  });
  drawingUtils.drawLandmarks(landmarks, {
    color: "#d84f32",
    fillColor: "#f7f2ea",
    lineWidth: 1,
    radius: 4
  });
}

function updateRecognition(result) {
  const category = result.gestures?.[0]?.[0];
  els.builtinGesture.textContent = category ? translateBuiltin(category.categoryName) : "--";

  const landmarks = result.landmarks?.[0];
  if (!landmarks) {
    els.prototypeMatch.textContent = prototypes.length ? "unknown" : "未录入";
    els.similarityScore.textContent = "--";
    els.triggerState.textContent = "未检测到手";
    return;
  }

  const vector = extractFeatureVector(landmarks, result.worldLandmarks?.[0]);
  sendRecognitionFrame(vector);
}

async function startCountdownRecording() {
  const name = els.gestureNameInput.value.trim();
  if (!name) {
    els.recordHint.textContent = "请先输入动作名称。";
    els.gestureNameInput.focus();
    return;
  }
  if (!recognizer) {
    els.recordHint.textContent = "模型仍在加载，请稍后再录入。";
    return;
  }
  if (!mediaStream) {
    const started = await startCamera();
    if (!started) return;
  }

  window.clearInterval(countdownTimer);
  let remaining = 3;
  isCountdownOpen = true;
  els.countdownValue.textContent = String(remaining);
  els.countdownScreen.hidden = false;
  await syncCountdownPreview();
  updateRecordButton();

  countdownTimer = window.setInterval(async () => {
    remaining -= 1;
    if (remaining > 0) {
      els.countdownValue.textContent = String(remaining);
      return;
    }
    window.clearInterval(countdownTimer);
    isCountdownOpen = false;
    els.countdownScreen.hidden = true;
    updateRecordButton();
    await beginRecording();
  }, 1000);
}

async function syncCountdownPreview() {
  if (!els.countdownWebcam || !mediaStream) return;
  if (els.countdownWebcam.srcObject !== mediaStream) {
    els.countdownWebcam.srcObject = mediaStream;
  }
  try {
    await els.countdownWebcam.play();
  } catch (error) {
    console.warn("Countdown camera preview could not autoplay.", error);
  }
}

async function beginRecording() {
  const name = els.gestureNameInput.value.trim();
  if (!name) {
    els.recordHint.textContent = "请先输入动作名称。";
    els.gestureNameInput.focus();
    return;
  }

  try {
    const state = await apiRequest("/api/recordings/start", {
      method: "POST",
      body: {
        name,
        action: els.actionSelect.value,
        kind: els.gestureKindSelect.value,
        holdMs: Number(els.holdMsSelect.value)
      }
    });
    els.recordHint.textContent = recordingPhaseHint({
      active: true,
      phase: "sampling",
      kind: els.gestureKindSelect.value,
      sampleCount: 0,
      sampleTarget: sampleTarget()
    });
    applyServiceState(state);
  } catch (error) {
    console.error(error);
    els.recordHint.textContent = "录入启动失败，请确认识别服务正在运行。";
  }
}

async function stopRecording(options = {}) {
  try {
    applyServiceState(await apiRequest("/api/recordings/cancel", { method: "POST" }));
  } catch (error) {
    console.error(error);
  } finally {
    if (!options.keepHint) {
      els.recordHint.textContent = recordingHint();
    }
  }
}

function recordingHint() {
  return `先选择静态姿态或动态轨迹，点击录入后倒数 3 秒并采集 ${sampleTarget()} 帧建立手势原型。`;
}

function sendRecognitionFrame(vector) {
  if (!recognitionSocket || recognitionSocket.readyState !== WebSocket.OPEN) {
    els.triggerState.textContent = "识别服务未连接";
    return;
  }
  recognitionSocket.send(JSON.stringify({ type: "frame", vector }));
}

async function apiRequest(path, options = {}) {
  const response = await fetch(path, {
    method: options.method || "GET",
    headers: options.body ? { "Content-Type": "application/json" } : undefined,
    body: options.body ? JSON.stringify(options.body) : undefined
  });

  if (!response.ok) {
    throw new Error(`API ${path} failed: ${response.status}`);
  }

  return response.json();
}

function applyServiceState(state) {
  if (state.config) {
    serviceConfig = state.config;
  }

  if (state.prototypes) {
    prototypes = state.prototypes;
    renderPrototypes();
  }

  if (state.recording) {
    isRecording = state.recording.active;
    els.sampleCount.textContent = recordingProgressText(state.recording);
    if (isRecording && state.recording.kind && els.gestureKindSelect) {
      els.gestureKindSelect.value = state.recording.kind;
    }
    els.cancelRecordBtn.disabled = !isRecording;
    updateRecordButton();
    if (isRecording) {
      els.recordHint.textContent = recordingPhaseHint(state.recording);
    }
  }

  if (state.recordingComplete) {
    els.recordHint.textContent = `已录入“${state.recordingComplete.name}”为${kindLabel(state.recordingComplete.kind)}，现在可直接识别。`;
    if (els.gestureKindSelect) {
      els.gestureKindSelect.value = state.recordingComplete.kind || els.gestureKindSelect.value;
    }
    els.gestureNameInput.value = "";
  }

  if (state.recognition) {
    const recognition = state.recognition;
    els.prototypeMatch.textContent = recognition.name;
    els.similarityScore.textContent =
      recognition.score === null || recognition.score === undefined
        ? recognition.motionLabel || "--"
        : `${recognition.score.toFixed(3)} · ${recognition.motionLabel}`;
    els.triggerState.textContent = recognition.triggerState;
  }

  if (state.vehicle) {
    applyVehicleState(state.vehicle);
  }
}

function updateRecordButton() {
  els.recordBtn.disabled = isRecording || isCountdownOpen || !recognizer;
  if (els.gestureKindSelect) {
    els.gestureKindSelect.disabled = isRecording || isCountdownOpen;
  }
}

async function createRecognizer(vision) {
  const options = {
    baseOptions: {
      modelAssetPath: MODEL_PATH,
      delegate: "GPU"
    },
    runningMode: "VIDEO",
    numHands: 1
  };

  try {
    return await GestureRecognizer.createFromOptions(vision, options);
  } catch (error) {
    console.warn("GPU delegate unavailable, falling back to CPU.", error);
    return GestureRecognizer.createFromOptions(vision, {
      ...options,
      baseOptions: {
        modelAssetPath: MODEL_PATH,
        delegate: "CPU"
      }
    });
  }
}

function renderPrototypes() {
  els.prototypeCount.textContent = `${prototypes.length} 个`;
  if (!prototypes.length) {
    els.prototypeList.innerHTML = `<div class="empty-list">暂无动作，录入后会显示在这里。</div>`;
    return;
  }

  els.prototypeList.innerHTML = "";
  for (const prototype of prototypes) {
    const item = document.createElement("div");
    item.className = "prototype-item";
    item.innerHTML = `
      <div>
        <strong>${escapeHtml(prototype.name)}</strong>
        <span>${kindLabel(prototype.kind)} · ${actionLabel(prototype.action)}</span>
      </div>
      <button type="button" aria-label="删除 ${escapeHtml(prototype.name)}">删除</button>
    `;
    item.querySelector("button").addEventListener("click", async () => {
      try {
        applyServiceState(await apiRequest(`/api/prototypes/${prototype.id}`, { method: "DELETE" }));
      } catch (error) {
        console.error(error);
      }
    });
    els.prototypeList.append(item);
  }
}

async function clearPrototypes() {
  try {
    applyServiceState(await apiRequest("/api/prototypes", { method: "DELETE" }));
    els.prototypeMatch.textContent = "未录入";
    els.similarityScore.textContent = "--";
  } catch (error) {
    console.error(error);
  }
}

function applyVehicleState(vehicle) {
  els.vehiclePower.textContent = vehicle.power;
  els.volumeSlider.value = vehicle.volume;
  els.tempSlider.value = vehicle.temperature;
  els.phoneState.textContent = vehicle.phone;
  els.featureState.textContent = vehicle.feature;
}

function resizeCanvas() {
  const width = els.webcam.videoWidth;
  const height = els.webcam.videoHeight;
  if (!width || !height) return;
  if (els.overlay.width !== width || els.overlay.height !== height) {
    els.overlay.width = width;
    els.overlay.height = height;
  }
}

function translateBuiltin(name) {
  const labels = {
    Closed_Fist: "握拳",
    Open_Palm: "手掌张开",
    Pointing_Up: "单指向上",
    Thumb_Down: "拇指向下",
    Thumb_Up: "拇指向上",
    Victory: "胜利手势",
    ILoveYou: "I Love You",
    None: "未识别"
  };
  return labels[name] || name;
}

function actionLabel(action) {
  const labels = {
    wake: "启动 / 唤醒",
    confirm: "确认 / 执行",
    volume_up: "音量增加",
    volume_down: "音量降低",
    next_feature: "切换功能",
    answer_call: "接听电话",
    hangup_call: "挂断电话",
    home: "返回主页"
  };
  return labels[action] || action;
}

function kindLabel(kind) {
  return kind === "dynamic" ? "动态轨迹" : "静态姿态";
}

function sampleTarget() {
  return serviceConfig?.sampleTarget || 45;
}

function recordingProgressText(recording) {
  if (!recording?.active) {
    return `0 / ${sampleTarget()} 帧`;
  }
  return `采样 ${recording.sampleCount ?? recording.count ?? 0} / ${recording.sampleTarget ?? sampleTarget()} 帧`;
}

function recordingPhaseHint(recording) {
  if (recording?.phase === "sampling") {
    const count = recording.sampleCount ?? 0;
    const target = recording.sampleTarget ?? sampleTarget();
    return `正在录入${kindLabel(recording.kind)}：${count} / ${target} 帧。`;
  }
  return recordingHint();
}

function escapeHtml(value) {
  return value.replace(/[&<>"']/g, (char) => {
    const entities = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
    return entities[char];
  });
}
