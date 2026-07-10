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
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class OwnerGestureControlService {

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
        Map<String, OwnerGestureControlBinding> bindings = bindingRepository
                .findByGestureCodeIn(gestures.stream().map(item -> stringValue(item.get("gestureCode"))).toList())
                .stream()
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

    @Transactional
    public Map<String, Object> saveControlSettings(Map<String, Object> payload) {
        Object rawSettings = payload == null ? null : payload.get("settings");
        if (!(rawSettings instanceof List<?> settings)) {
            return getControlSettings();
        }

        for (Object rawItem : settings) {
            if (!(rawItem instanceof Map<?, ?> item)) {
                continue;
            }
            String gestureCode = stringValue(item.get("gestureCode")).trim();
            if (gestureCode.isBlank()) {
                continue;
            }

            String actionType = normalizeAction(item.get("actionType"));
            boolean enabled = Boolean.TRUE.equals(item.get("enabled")) && !"NONE".equals(actionType);
            OwnerGestureControlBinding binding = bindingRepository.findByGestureCode(gestureCode)
                    .orElseGet(OwnerGestureControlBinding::new);
            binding.setGestureCode(gestureCode);
            binding.setGestureName(defaultIfBlank(stringValue(item.get("gestureName")), gestureCode));
            binding.setGestureKind(defaultIfBlank(stringValue(item.get("gestureKind")), stringValue(item.get("kind"))));
            binding.setGestureSource(defaultIfBlank(stringValue(item.get("gestureSource")), stringValue(item.get("source"))));
            binding.setActionType(actionType);
            binding.setEnabled(enabled);
            bindingRepository.save(binding);
        }

        return getControlSettings();
    }

    public Map<String, Object> executeControl(Map<String, Object> payload) {
        String gestureCode = stringValue(payload == null ? null : payload.get("gestureCode")).trim();
        String gestureName = stringValue(payload == null ? null : payload.get("gestureName")).trim();
        Object confidence = payload == null ? null : payload.get("confidence");

        Optional<OwnerGestureControlBinding> optional = bindingRepository.findByGestureCode(gestureCode);
        if (optional.isEmpty() && !gestureName.isBlank()) {
            optional = availableGestures().stream()
                    .filter(item -> gestureName.equals(stringValue(item.get("gestureName"))))
                    .map(item -> stringValue(item.get("gestureCode")))
                    .filter(code -> !code.isBlank())
                    .findFirst()
                    .flatMap(bindingRepository::findByGestureCode);
        }

        if (optional.isEmpty()) {
            return Map.of(
                    "enabled", false,
                    "gestureCode", gestureCode,
                    "gestureName", gestureName,
                    "actionType", "NONE",
                    "actionLabel", ACTION_LABELS.get("NONE")
            );
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

    private List<Map<String, Object>> availableGestures() {
        Map<String, Map<String, Object>> gestures = new LinkedHashMap<>();
        Map<String, Object> library = algorithmClient.getOwnerGestureLibrary();
        collectGestures(gestures, library.get("gestures"));
        collectGestures(gestures, library.get("prototypes"));
        collectGestures(gestures, algorithmClient.getOwnerGesturePrototypes().get("prototypes"));
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
        gesture.put("holdMs", holdMs);
        return gesture;
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
