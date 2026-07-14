package com.visiondrive.security;

import com.visiondrive.model.entity.User;
import com.visiondrive.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Slf4j
@Component
@RequiredArgsConstructor
@Order(Ordered.HIGHEST_PRECEDENCE)
public class LegacyPasswordMigrationRunner implements ApplicationRunner {
    private static final String BCRYPT_PATTERN = "^\\$2[aby]\\$\\d{2}\\$[./A-Za-z0-9]{53}$";

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    @Override
    @Transactional
    public void run(ApplicationArguments arguments) {
        List<User> legacyUsers = userRepository.findAll().stream()
                .filter(user -> user.getPassword() == null || !user.getPassword().matches(BCRYPT_PATTERN))
                .toList();
        legacyUsers.forEach(user -> user.setPassword(passwordEncoder.encode(
                user.getPassword() == null ? "" : user.getPassword()
        )));
        if (!legacyUsers.isEmpty()) {
            userRepository.saveAllAndFlush(legacyUsers);
            log.info("历史明文密码升级为 BCrypt: users={}", legacyUsers.size());
        }

        boolean invalidPasswordRemains = userRepository.findAll().stream()
                .anyMatch(user -> user.getPassword() == null || !user.getPassword().matches(BCRYPT_PATTERN));
        if (invalidPasswordRemains) {
            throw new IllegalStateException("数据库仍存在非 BCrypt 用户密码，拒绝启动认证服务");
        }
    }
}
