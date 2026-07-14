package com.visiondrive.service;

import com.visiondrive.client.AlgorithmClient;
import com.visiondrive.model.entity.OwnerGestureControlBinding;
import com.visiondrive.repository.OwnerGestureControlBindingRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Collectors;

import static com.visiondrive.client.AlgorithmClient.OWNER_GESTURE_ALGORITHM;

@Service
@RequiredArgsConstructor
public class OwnerGestureControlService {

    private static final Set<String> DINO_CONFIG_KEYS = Set.of(
            "activeAlgorithm",
            "dinov2MatchThreshold",
            "dinov2FrameIntervalMs",
            "sampleTarget",
            "defaultHoldMs",
            "triggerCooldownMs"
    );
    private static final Set<String> MUTABLE_DINO_CONFIG_KEYS = Set.of(
            "dinov2MatchThreshold",
            "dinov2FrameIntervalMs",
            "defaultHoldMs",
            "triggerCooldownMs"
    );

    private static final List<Map<String, String>> ACTION_OPTIONS = List.of(
            action("NONE", "不触发控制"),
            action("WAKE_SYSTEM", "启动/唤醒系统"),
            action("CONFIRM", "确认当前操作"),
            action("VOLUME_UP", "音量增加"),
            action("VOLUME_DOWN", "音量降低"),
            action("NEXT_MEDIA", "切换下一首"),
            action("CLIMATE_UP", "空调升温"),
            action("CLIMATE_DOWN", "空调降温"),
            action("ANSWER_CALL", "接听电话"),
            action("HANG_UP", "挂断电话"),
            action("OPEN_NAVIGATION", "打开导航"),
            action("RETURN_HOME", "返回驾驶主页")
    );

    private static final Map<String, String> ACTION_LABELS = ACTION_OPTIONS.stream()
            .collect(Collectors.toUnmodifiableMap(item -> item.get("actionType"), item -> item.get("actionLabel")));

    private static final Map<String, String> ACTION_ALIASES = Map.ofEntries(
            Map.entry("wake", "WAKE_SYSTEM"),
            Map.entry("confirm", "CONFIRM"),
            Map.entry("volume_up", "VOLUME_UP"),
            Map.entry("volume_down", "VOLUME_DOWN"),
            Map.entry("next_feature", "NEXT_MEDIA"),
            Map.entry("answer_call", "ANSWER_CALL"),
            Map.entry("hangup_call", "HANG_UP"),
            Map.entry("home", "RETURN_HOME"),
            Map.entry("启动 / 唤醒", "WAKE_SYSTEM"),
            Map.entry("启动/唤醒系统", "WAKE_SYSTEM"),
            Map.entry("确认 / 执行", "CONFIRM"),
            Map.entry("确认当前操作", "CONFIRM"),
            Map.entry("音量增加", "VOLUME_UP"),
            Map.entry("音量降低", "VOLUME_DOWN"),
            Map.entry("切换功能", "NEXT_MEDIA"),
            Map.entry("切换下一首", "NEXT_MEDIA"),
            Map.entry("接听电话", "ANSWER_CALL"),
            Map.entry("挂断电话", "HANG_UP"),
            Map.entry("返回主页", "RETURN_HOME"),
            Map.entry("返回驾驶主页", "RETURN_HOME")
    );

    private final OwnerGestureControlBindingRepository bindingRepository;
    private final AlgorithmClient algorithmClient;

    public Map<String, Object> getControlSettings() {
        List<Map<String, Object>> gestures = availableGestures();
        List<String> gestureCodes = gestures.stream()
                .map(item -> stringValue(item.get("gestureCode")))
                .toList();
        Map<String, OwnerGestureControlBinding> bindings = gestureCodes.isEmpty()
                ? Map.of()
                : bindingRepository.findByGestureCodeIn(gestureCodes).stream()
                        .collect(Collectors.toMap(OwnerGestureControlBinding::getGestureCode, item -> item));

        List<Map<String, Object>> settings = gestures.stream()
                .map(gesture -> mergeGestureBinding(gesture, bindings.get(stringValue(gesture.get("gestureCode")))))
                .toList();

        return Map.of(
                "settings", settings,
                "actions", ACTION_OPTIONS,
                "bindings", settings
        );
    }

    public Map<String, Object> getPrototypeLibrary() {
        List<Map<String, Object>> prototypes = availableGestures();
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("algorithm", OWNER_GESTURE_ALGORITHM);
        result.put("presetGestures", true);
        result.put("gestures", prototypes);
        result.put("prototypes", prototypes);
        return result;
    }

    public Map<String, Object> getRecognitionState() {
        Map<String, Object> rawState = algorithmClient.getOwnerGestureState();
        Map<String, Object> state = new LinkedHashMap<>(rawState);
        state.put("algorithm", Map.of(
                "active", OWNER_GESTURE_ALGORITHM,
                "presetGestures", true
        ));
        state.put("prototypes", normalizePrototypes(rawState.get("prototypes")));
        state.put("config", sanitizeConfig(rawState.get("config")));
        return state;
    }

    public Map<String, Object> getRecognitionConfig() {
        Map<String, Object> raw = algorithmClient.getOwnerGestureConfig();
        return Map.of("config", sanitizeConfig(raw.get("config")));
    }

    public Map<String, Object> updateRecognitionConfig(Map<String, Object> payload) {
        Map<String, Object> patch = new LinkedHashMap<>();
        if (payload != null) {
            payload.forEach((key, value) -> {
                if (MUTABLE_DINO_CONFIG_KEYS.contains(key)) {
                    patch.put(key, value);
                }
            });
        }
        if (patch.isEmpty()) {
            return getRecognitionConfig();
        }
        Map<String, Object> updated = algorithmClient.patchOwnerGestureConfig(patch);
        return Map.of("config", sanitizeConfig(updated.get("config")));
    }

    @Transactional
    public Map<String, Object> saveControlSettings(Map<String, Object> payload) {
        List<Map<String, Object>> gestures = availableGestures();
        Map<String, Map<String, Object>> allowedGestures = gestures.stream().collect(Collectors.toMap(
                item -> stringValue(item.get("gestureCode")),
                item -> item,
                (first, ignored) -> first,
                LinkedHashMap::new
        ));
        Object rawSettings = payload == null ? null : payload.get("settings");
        if (!(rawSettings instanceof List<?> settings)) {
            return getControlSettings();
        }

        for (Object rawItem : settings) {
            if (!(rawItem instanceof Map<?, ?> item)) {
                continue;
            }
            String gestureCode = stringValue(item.get("gestureCode")).trim();
            Map<String, Object> prototype = allowedGestures.get(gestureCode);
            if (gestureCode.isBlank() || prototype == null) {
                continue;
            }

            String actionType = normalizeAction(item.get("actionType"));
            boolean enabled = Boolean.TRUE.equals(item.get("enabled")) && !"NONE".equals(actionType);
            OwnerGestureControlBinding binding = bindingRepository.findByGestureCode(gestureCode)
                    .orElseGet(OwnerGestureControlBinding::new);
            binding.setGestureCode(gestureCode);
            binding.setGestureName(stringValue(prototype.get("gestureName")));
            binding.setGestureKind(stringValue(prototype.get("gestureKind")));
            binding.setGestureSource(defaultIfBlank(stringValue(prototype.get("gestureSource")), "custom"));
            binding.setActionType(actionType);
            binding.setEnabled(enabled);
            bindingRepository.save(binding);
        }

        deleteObsoleteBindings(allowedGestures.keySet());

        return getControlSettings();
    }

    public Map<String, Object> executeControl(Map<String, Object> payload) {
        String gestureCode = stringValue(payload == null ? null : payload.get("gestureCode")).trim();
        String gestureName = stringValue(payload == null ? null : payload.get("gestureName")).trim();
        Object confidence = payload == null ? null : payload.get("confidence");

        List<Map<String, Object>> available = availableGestures();
        Map<String, Object> prototype = available.stream()
                .filter(item -> gestureCode.equals(stringValue(item.get("gestureCode"))))
                .findFirst()
                .orElseGet(() -> available.stream()
                        .filter(item -> !gestureName.isBlank() && gestureName.equals(stringValue(item.get("gestureName"))))
                        .findFirst()
                        .orElse(null));

        if (prototype == null) {
            return disabledControl(gestureCode, gestureName);
        }

        String activeGestureCode = stringValue(prototype.get("gestureCode"));
        String activeGestureName = stringValue(prototype.get("gestureName"));

        Optional<OwnerGestureControlBinding> optional = bindingRepository.findByGestureCode(activeGestureCode);

        if (optional.isEmpty()) {
            return disabledControl(activeGestureCode, activeGestureName);
        }

        OwnerGestureControlBinding binding = optional.get();
        String actionType = normalizeAction(binding.getActionType());
        boolean enabled = Boolean.TRUE.equals(binding.getEnabled()) && !"NONE".equals(actionType);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("enabled", enabled);
        result.put("gestureCode", binding.getGestureCode());
        result.put("gestureName", binding.getGestureName());
        result.put("gestureKind", binding.getGestureKind());
        result.put("gestureSource", binding.getGestureSource());
        result.put("actionType", actionType);
        result.put("actionLabel", ACTION_LABELS.getOrDefault(actionType, actionType));
        result.put("confidence", confidence);
        return result;
    }

    @Transactional
    public void deleteBinding(String gestureCode) {
        if (gestureCode == null || gestureCode.isBlank()) {
            return;
        }
        bindingRepository.findByGestureCode(gestureCode).ifPresent(bindingRepository::delete);
    }

    @Transactional
    public int reconcileBindings() {
        Set<String> activeGestureCodes = availableGestures().stream()
                .map(item -> stringValue(item.get("gestureCode")))
                .filter(code -> !code.isBlank())
                .collect(Collectors.toSet());
        return deleteObsoleteBindings(activeGestureCodes);
    }

    private List<Map<String, Object>> availableGestures() {
        return normalizePrototypes(algorithmClient.getOwnerGesturePrototypes().get("prototypes"));
    }

    private List<Map<String, Object>> normalizePrototypes(Object rawItems) {
        Map<String, Map<String, Object>> gestures = new LinkedHashMap<>();
        collectGestures(gestures, rawItems);
        return new ArrayList<>(gestures.values());
    }

    private void collectGestures(Map<String, Map<String, Object>> output, Object rawItems) {
        if (!(rawItems instanceof List<?> items)) {
            return;
        }
        for (Object rawItem : items) {
            if (!(rawItem instanceof Map<?, ?> item)) {
                continue;
            }
            if (!OWNER_GESTURE_ALGORITHM.equals(stringValue(item.get("algorithm")))) {
                continue;
            }
            Map<String, Object> normalized = normalizeGesture(item);
            String gestureCode = stringValue(normalized.get("gestureCode"));
            if (!gestureCode.isBlank()) {
                output.putIfAbsent(gestureCode, normalized);
            }
        }
    }

    private Map<String, Object> normalizeGesture(Map<?, ?> item) {
        String gestureCode = firstNonBlank(item.get("gestureCode"), item.get("id"), item.get("code"), item.get("name"));
        String gestureName = firstNonBlank(item.get("gestureName"), item.get("name"), item.get("label"), gestureCode);
        String source = firstNonBlank(item.get("source"), item.get("gestureSource"));
        if (source.isBlank()) {
            source = "custom";
        }
        String kind = firstNonBlank(item.get("gestureKind"), item.get("kind"));
        Integer holdMs = normalizeHoldMs(firstNonNull(item.get("holdMs"), item.get("hold_ms")), 1200);
        Map<String, Object> gesture = new LinkedHashMap<>();
        gesture.put("gestureCode", gestureCode);
        gesture.put("gestureName", gestureName);
        gesture.put("gestureKind", kind);
        gesture.put("gestureSource", source);
        gesture.put("algorithm", OWNER_GESTURE_ALGORITHM);
        gesture.put("holdMs", holdMs);
        return gesture;
    }

    private Map<String, Object> sanitizeConfig(Object rawConfig) {
        Map<String, Object> config = new LinkedHashMap<>();
        if (rawConfig instanceof Map<?, ?> values) {
            values.forEach((key, value) -> {
                String name = stringValue(key);
                if (DINO_CONFIG_KEYS.contains(name)) {
                    config.put(name, value);
                }
            });
        }
        config.put("activeAlgorithm", OWNER_GESTURE_ALGORITHM);
        config.put("sampleTarget", 12);
        return config;
    }

    private int deleteObsoleteBindings(Set<String> activeGestureCodes) {
        List<OwnerGestureControlBinding> obsolete = bindingRepository.findAll().stream()
                .filter(binding -> !activeGestureCodes.contains(binding.getGestureCode()))
                .toList();
        if (!obsolete.isEmpty()) {
            bindingRepository.deleteAll(obsolete);
        }
        return obsolete.size();
    }

    private Map<String, Object> disabledControl(String gestureCode, String gestureName) {
        return Map.of(
                "enabled", false,
                "gestureCode", gestureCode,
                "gestureName", gestureName,
                "actionType", "NONE",
                "actionLabel", ACTION_LABELS.get("NONE")
        );
    }

    private Map<String, Object> mergeGestureBinding(Map<String, Object> gesture, OwnerGestureControlBinding binding) {
        String actionType = binding == null ? "NONE" : normalizeAction(binding.getActionType());
        boolean enabled = binding != null && Boolean.TRUE.equals(binding.getEnabled()) && !"NONE".equals(actionType);
        Map<String, Object> setting = new LinkedHashMap<>(gesture);
        setting.put("actionType", actionType);
        setting.put("actionLabel", ACTION_LABELS.getOrDefault(actionType, actionType));
        setting.put("enabled", enabled);
        setting.put("bound", enabled);
        setting.put("holdMs", normalizeHoldMs(setting.get("holdMs"), 1200));
        return setting;
    }

    private static String normalizeAction(Object action) {
        String value = stringValue(action).trim();
        if (value.isBlank()) {
            return "NONE";
        }
        String upper = value.toUpperCase(Locale.ROOT);
        if (ACTION_LABELS.containsKey(upper)) {
            return upper;
        }
        return ACTION_ALIASES.getOrDefault(value, "NONE");
    }

    private static Map<String, String> action(String actionType, String actionLabel) {
        return Map.of("actionType", actionType, "actionLabel", actionLabel);
    }

    private static String firstNonBlank(Object... values) {
        for (Object value : values) {
            String text = stringValue(value).trim();
            if (!text.isBlank()) {
                return text;
            }
        }
        return "";
    }

    private static String defaultIfBlank(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value;
    }

    private static Object firstNonNull(Object... values) {
        for (Object value : values) {
            if (value != null) {
                return value;
            }
        }
        return null;
    }

    private static Integer normalizeHoldMs(Object value, Integer fallback) {
        if (value instanceof Number number) {
            int numeric = number.intValue();
            return numeric > 0 ? numeric : fallback;
        }
        String text = stringValue(value).trim();
        if (!text.isBlank()) {
            try {
                int numeric = Integer.parseInt(text);
                return numeric > 0 ? numeric : fallback;
            } catch (NumberFormatException ignored) {
                return fallback;
            }
        }
        return fallback;
    }

    private static String stringValue(Object value) {
        return Objects.toString(value, "");
    }
}
