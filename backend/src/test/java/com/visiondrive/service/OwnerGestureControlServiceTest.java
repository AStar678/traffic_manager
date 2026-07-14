package com.visiondrive.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.visiondrive.client.AlgorithmClient;
import com.visiondrive.model.entity.OwnerGestureControlBinding;
import com.visiondrive.repository.OwnerGestureControlBindingRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.web.client.RestTemplate;

import java.lang.reflect.Proxy;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;

class OwnerGestureControlServiceTest {

    private final List<OwnerGestureControlBinding> storedBindings = new ArrayList<>();
    private final List<OwnerGestureControlBinding> deletedBindings = new ArrayList<>();
    private StubAlgorithmClient algorithmClient;
    private OwnerGestureControlService service;

    @BeforeEach
    void setUp() {
        storedBindings.clear();
        deletedBindings.clear();
        algorithmClient = new StubAlgorithmClient();
        service = new OwnerGestureControlService(repositoryStub(), algorithmClient);
    }

    @Test
    void exposesDinov2SystemAndUserPrototypes() {
        algorithmClient.prototypes = List.of(
                prototype("deep-1", "视频挥手", "dinov2_tcn_prototype", "custom"),
                prototype("Open_Palm", "手掌张开", "dinov2_tcn_prototype", "built_in"),
                prototype("legacy-open", "旧系统手势", "mediapipe_prototype", "built_in")
        );

        Map<String, Object> library = service.getPrototypeLibrary();

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> gestures = (List<Map<String, Object>>) library.get("gestures");
        assertEquals("dinov2_tcn_prototype", library.get("algorithm"));
        assertEquals(true, library.get("presetGestures"));
        assertEquals(2, gestures.size());
        assertEquals("deep-1", gestures.get(0).get("gestureCode"));
        assertEquals("custom", gestures.get(0).get("gestureSource"));
        assertEquals("Open_Palm", gestures.get(1).get("gestureCode"));
        assertEquals("built_in", gestures.get(1).get("gestureSource"));
    }

    @Test
    void removesEveryBindingThatDoesNotBelongToCurrentDinov2Prototypes() {
        algorithmClient.prototypes = List.of(
                prototype("deep-1", "视频挥手", "dinov2_tcn_prototype", "custom"),
                prototype("Open_Palm", "手掌张开", "dinov2_tcn_prototype", "built_in")
        );
        OwnerGestureControlBinding active = binding("deep-1", "custom");
        OwnerGestureControlBinding activeSystem = binding("Open_Palm", "built_in");
        OwnerGestureControlBinding oldSystem = binding("Thumb_Up", "built_in");
        OwnerGestureControlBinding oldCustom = binding("legacy-custom", "custom");
        storedBindings.addAll(List.of(active, activeSystem, oldSystem, oldCustom));

        assertEquals(2, service.reconcileBindings());
        assertEquals(List.of(oldSystem, oldCustom), deletedBindings);
        assertEquals(List.of(active, activeSystem), storedBindings);
    }

    @Test
    void executesCurrentSystemGestureBinding() {
        algorithmClient.prototypes = List.of(
                prototype("deep-1", "视频挥手", "dinov2_tcn_prototype", "custom"),
                prototype("Open_Palm", "手掌张开", "dinov2_tcn_prototype", "built_in")
        );
        storedBindings.add(binding("Open_Palm", "built_in"));

        Map<String, Object> result = service.executeControl(Map.of(
                "gestureCode", "Open_Palm",
                "gestureName", "手掌张开",
                "confidence", 0.99
        ));

        assertEquals(true, result.get("enabled"));
        assertEquals("VOLUME_UP", result.get("actionType"));
    }

    @Test
    void savesCurrentSystemAndUserPrototypeBindings() {
        algorithmClient.prototypes = List.of(
                prototype("deep-1", "视频挥手", "dinov2_tcn_prototype", "custom"),
                prototype("Open_Palm", "手掌张开", "dinov2_tcn_prototype", "built_in")
        );

        service.saveControlSettings(Map.of("settings", List.of(
                Map.of(
                        "gestureCode", "Open_Palm",
                        "gestureName", "手掌张开",
                        "gestureSource", "built_in",
                        "actionType", "VOLUME_DOWN",
                        "enabled", true
                ),
                Map.of(
                        "gestureCode", "deep-1",
                        "gestureName", "伪造名称",
                        "gestureSource", "system",
                        "actionType", "VOLUME_UP",
                        "enabled", true
                )
        )));

        assertEquals(2, storedBindings.size());
        OwnerGestureControlBinding systemBinding = storedBindings.stream()
                .filter(item -> "Open_Palm".equals(item.getGestureCode()))
                .findFirst().orElseThrow();
        OwnerGestureControlBinding customBinding = storedBindings.stream()
                .filter(item -> "deep-1".equals(item.getGestureCode()))
                .findFirst().orElseThrow();
        assertEquals("built_in", systemBinding.getGestureSource());
        assertEquals("VOLUME_DOWN", systemBinding.getActionType());
        assertEquals("视频挥手", customBinding.getGestureName());
        assertEquals("custom", customBinding.getGestureSource());
        assertEquals("VOLUME_UP", customBinding.getActionType());
    }

    @Test
    void stateHidesLegacyAlgorithmOptionsAndParameters() {
        algorithmClient.state = Map.of(
                "algorithm", Map.of("active", "dinov2_tcn_prototype", "options", List.of(
                        Map.of("id", "mediapipe_prototype"),
                        Map.of("id", "dinov2_tcn_prototype")
                )),
                "prototypes", List.of(
                        prototype("deep-1", "视频挥手", "dinov2_tcn_prototype", "custom"),
                        prototype("Open_Palm", "手掌张开", "dinov2_tcn_prototype", "built_in"),
                        prototype("legacy-open", "旧系统手势", "mediapipe_prototype", "built_in")
                ),
                "config", Map.of(
                        "activeAlgorithm", "dinov2_tcn_prototype",
                        "dinov2MatchThreshold", 0.72,
                        "staticMatchThreshold", 0.70,
                        "sampleTarget", 45
                )
        );

        Map<String, Object> state = service.getRecognitionState();

        @SuppressWarnings("unchecked")
        Map<String, Object> algorithm = (Map<String, Object>) state.get("algorithm");
        @SuppressWarnings("unchecked")
        Map<String, Object> config = (Map<String, Object>) state.get("config");
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> prototypes = (List<Map<String, Object>>) state.get("prototypes");
        assertEquals(Map.of("active", "dinov2_tcn_prototype", "presetGestures", true), algorithm);
        assertEquals(2, prototypes.size());
        assertEquals(12, config.get("sampleTarget"));
        assertFalse(config.containsKey("staticMatchThreshold"));
    }

    @Test
    void configUpdateIgnoresLegacyMatchingParameters() {
        algorithmClient.config = Map.of(
                "activeAlgorithm", "dinov2_tcn_prototype",
                "dinov2MatchThreshold", 0.80,
                "sampleTarget", 12
        );

        Map<String, Object> result = service.updateRecognitionConfig(Map.of(
                "dinov2MatchThreshold", 0.80,
                "staticMatchThreshold", 0.95,
                "palmDirectionThreshold", 0.90
        ));

        assertEquals(Map.of("dinov2MatchThreshold", 0.80), algorithmClient.lastConfigPatch);
        @SuppressWarnings("unchecked")
        Map<String, Object> config = (Map<String, Object>) result.get("config");
        assertEquals(0.80, config.get("dinov2MatchThreshold"));
        assertFalse(config.containsKey("staticMatchThreshold"));
    }

    @SuppressWarnings("unchecked")
    private OwnerGestureControlBindingRepository repositoryStub() {
        return (OwnerGestureControlBindingRepository) Proxy.newProxyInstance(
                OwnerGestureControlBindingRepository.class.getClassLoader(),
                new Class<?>[]{OwnerGestureControlBindingRepository.class},
                (proxy, method, args) -> switch (method.getName()) {
                    case "findAll" -> List.copyOf(storedBindings);
                    case "findByGestureCode" -> storedBindings.stream()
                            .filter(item -> item.getGestureCode().equals(args[0]))
                            .findFirst();
                    case "findByGestureCodeIn" -> storedBindings.stream()
                            .filter(item -> ((List<String>) args[0]).contains(item.getGestureCode()))
                            .toList();
                    case "save" -> {
                        OwnerGestureControlBinding binding = (OwnerGestureControlBinding) args[0];
                        if (!storedBindings.contains(binding)) {
                            storedBindings.add(binding);
                        }
                        yield binding;
                    }
                    case "deleteAll" -> {
                        List<OwnerGestureControlBinding> deleted = (List<OwnerGestureControlBinding>) args[0];
                        deletedBindings.addAll(deleted);
                        storedBindings.removeAll(deleted);
                        yield null;
                    }
                    case "toString" -> "OwnerGestureControlBindingRepositoryStub";
                    default -> defaultValue(method.getReturnType());
                }
        );
    }

    private Object defaultValue(Class<?> type) {
        if (!type.isPrimitive()) return null;
        if (type == boolean.class) return false;
        if (type == long.class) return 0L;
        if (type == int.class) return 0;
        if (type == double.class) return 0D;
        return 0;
    }

    private Map<String, Object> prototype(String id, String name, String algorithm, String source) {
        return Map.of(
                "id", id,
                "name", name,
                "kind", "dynamic",
                "holdMs", 1200,
                "algorithm", algorithm,
                "source", source
        );
    }

    private OwnerGestureControlBinding binding(String code, String source) {
        OwnerGestureControlBinding binding = new OwnerGestureControlBinding();
        binding.setGestureCode(code);
        binding.setGestureName(code);
        binding.setGestureKind("dynamic");
        binding.setGestureSource(source);
        binding.setActionType("VOLUME_UP");
        binding.setEnabled(true);
        return binding;
    }

    private static final class StubAlgorithmClient extends AlgorithmClient {
        private List<Map<String, Object>> prototypes = List.of();
        private Map<String, Object> state = Map.of();
        private Map<String, Object> config = Map.of();
        private Map<String, Object> lastConfigPatch = Map.of();

        private StubAlgorithmClient() {
            super(new RestTemplate(), new ObjectMapper());
        }

        @Override
        public Map<String, Object> getOwnerGesturePrototypes() {
            return Map.of("prototypes", prototypes);
        }

        @Override
        public Map<String, Object> getOwnerGestureState() {
            return state;
        }

        @Override
        public Map<String, Object> getOwnerGestureConfig() {
            return Map.of("config", config);
        }

        @Override
        public Map<String, Object> patchOwnerGestureConfig(Map<String, Object> requestBody) {
            lastConfigPatch = Map.copyOf(requestBody);
            config = Map.copyOf(requestBody);
            return Map.of("config", config);
        }
    }
}
