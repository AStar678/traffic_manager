-- 用户隔离的三类识别结果表。
-- 每次识别保存一行，recognition_result 使用 JSON 字符串存储完整算法输出。

CREATE TABLE IF NOT EXISTS license_plate_recognition_result (
    user_id BIGINT NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    recognition_result LONGTEXT NOT NULL,
    image_source VARCHAR(2048) NOT NULL,
    PRIMARY KEY (user_id, created_at),
    CONSTRAINT fk_license_plate_result_user
        FOREIGN KEY (user_id) REFERENCES `user` (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS police_gesture_recognition_result (
    user_id BIGINT NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    recognition_result LONGTEXT NOT NULL,
    image_source VARCHAR(2048) NOT NULL,
    PRIMARY KEY (user_id, created_at),
    CONSTRAINT fk_police_gesture_result_user
        FOREIGN KEY (user_id) REFERENCES `user` (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS user_gesture_recognition_result (
    user_id BIGINT NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    recognition_result LONGTEXT NOT NULL,
    image_source VARCHAR(2048) NOT NULL,
    PRIMARY KEY (user_id, created_at),
    CONSTRAINT fk_user_gesture_result_user
        FOREIGN KEY (user_id) REFERENCES `user` (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
