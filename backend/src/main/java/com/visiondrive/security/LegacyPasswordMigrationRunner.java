package com.visiondrive.security;

import com.visiondrive.model.entity.User;
import com.visiondrive.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Slf4j
@Component
@RequiredArgsConstructor
public class LegacyPasswordMigrationRunner implements ApplicationRunner {
    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    @Override
    @Transactional
    public void run(ApplicationArguments arguments) {
        List<User> legacyUsers = userRepository.findAll().stream()
                .filter(user -> user.getPassword() != null && !user.getPassword().startsWith("$2"))
                .toList();
        legacyUsers.forEach(user -> user.setPassword(passwordEncoder.encode(user.getPassword())));
        if (!legacyUsers.isEmpty()) {
            userRepository.saveAll(legacyUsers);
            log.info("历史明文密码升级为 BCrypt: users={}", legacyUsers.size());
        }
    }
}
