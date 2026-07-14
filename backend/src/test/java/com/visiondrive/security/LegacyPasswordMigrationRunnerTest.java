package com.visiondrive.security;

import com.visiondrive.model.entity.User;
import com.visiondrive.repository.UserRepository;
import org.junit.jupiter.api.Test;
import org.springframework.boot.DefaultApplicationArguments;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
class LegacyPasswordMigrationRunnerTest {

    @Test
    void convertsEveryLegacyPlaintextPasswordToBcrypt() throws Exception {
        User first = user(1L, "password123");
        User second = user(2L, "another-password");
        List<User> users = new ArrayList<>(List.of(first, second));
        AtomicBoolean saved = new AtomicBoolean();
        UserRepository repository = repository(users, saved);
        BCryptPasswordEncoder encoder = new BCryptPasswordEncoder(4);

        new LegacyPasswordMigrationRunner(repository, encoder)
                .run(new DefaultApplicationArguments(new String[0]));

        assertTrue(saved.get());
        assertTrue(encoder.matches("password123", first.getPassword()));
        assertTrue(encoder.matches("another-password", second.getPassword()));
        assertTrue(users.stream().allMatch(user -> user.getPassword().matches(
                "^\\$2[aby]\\$\\d{2}\\$[./A-Za-z0-9]{53}$"
        )));
    }

    @Test
    void leavesExistingBcryptHashesUntouched() throws Exception {
        BCryptPasswordEncoder encoder = new BCryptPasswordEncoder(4);
        String storedHash = encoder.encode("password123");
        User user = user(1L, storedHash);
        AtomicBoolean saved = new AtomicBoolean();
        UserRepository repository = repository(List.of(user), saved);

        new LegacyPasswordMigrationRunner(repository, encoder)
                .run(new DefaultApplicationArguments(new String[0]));

        assertFalse(saved.get());
        assertEquals(storedHash, user.getPassword());
    }

    @SuppressWarnings("unchecked")
    private UserRepository repository(List<User> users, AtomicBoolean saved) {
        return (UserRepository) java.lang.reflect.Proxy.newProxyInstance(
                UserRepository.class.getClassLoader(),
                new Class<?>[]{UserRepository.class},
                (proxy, method, args) -> switch (method.getName()) {
                    case "findAll" -> users;
                    case "saveAllAndFlush" -> {
                        saved.set(true);
                        yield args[0];
                    }
                    default -> defaultValue(method.getReturnType());
                }
        );
    }

    private Object defaultValue(Class<?> type) {
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

    private User user(Long id, String password) {
        User user = new User();
        user.setId(id);
        user.setUsername("user_" + id);
        user.setPassword(password);
        return user;
    }
}
