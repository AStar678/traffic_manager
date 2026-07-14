package com.visiondrive.service;

import com.visiondrive.repository.SystemLogRepository;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Proxy;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.jupiter.api.Assertions.assertEquals;

class AlertServiceTest {

    @Test
    void clearsOnlyErrorLogsWithinNormalizedCurrentFilters() {
        CapturedDelete captured = new CapturedDelete(7);
        AlertService service = new AlertService(null, repository(captured));

        int deletedCount = service.clearErrorLogs("  owner_gesture  ", " failure ");

        assertEquals(7, deletedCount);
        assertEquals("owner_gesture", captured.module.get());
        assertEquals("failure", captured.event.get());
        assertEquals(1, captured.calls.get());
    }

    @Test
    void treatsBlankFiltersAsAllErrorLogs() {
        CapturedDelete captured = new CapturedDelete(3);
        AlertService service = new AlertService(null, repository(captured));

        int deletedCount = service.clearErrorLogs(" ", null);

        assertEquals(3, deletedCount);
        assertEquals(null, captured.module.get());
        assertEquals(null, captured.event.get());
        assertEquals(1, captured.calls.get());
    }

    private static SystemLogRepository repository(CapturedDelete captured) {
        return (SystemLogRepository) Proxy.newProxyInstance(
                SystemLogRepository.class.getClassLoader(),
                new Class<?>[]{SystemLogRepository.class},
                (proxy, method, args) -> {
                    if ("deleteErrorLogs".equals(method.getName())) {
                        captured.module.set((String) args[0]);
                        captured.event.set((String) args[1]);
                        captured.calls.incrementAndGet();
                        return captured.deletedCount;
                    }
                    return defaultValue(method.getReturnType());
                }
        );
    }

    private static Object defaultValue(Class<?> type) {
        if (!type.isPrimitive()) return null;
        if (type == boolean.class) return false;
        if (type == byte.class) return (byte) 0;
        if (type == short.class) return (short) 0;
        if (type == int.class) return 0;
        if (type == long.class) return 0L;
        if (type == float.class) return 0F;
        if (type == double.class) return 0D;
        if (type == char.class) return '\0';
        return null;
    }

    private static class CapturedDelete {
        private final int deletedCount;
        private final AtomicReference<String> module = new AtomicReference<>();
        private final AtomicReference<String> event = new AtomicReference<>();
        private final AtomicInteger calls = new AtomicInteger();

        private CapturedDelete(int deletedCount) {
            this.deletedCount = deletedCount;
        }
    }
}
