-- VisionDrive 数据库初始化脚本

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100),
    role VARCHAR(20) DEFAULT 'USER',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 推理记录表
CREATE TABLE IF NOT EXISTS inference_records (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    task_type VARCHAR(30) NOT NULL,
    input_type VARCHAR(20) NOT NULL,
    request_id VARCHAR(50) NOT NULL UNIQUE,
    user_id BIGINT,
    status VARCHAR(20) DEFAULT 'completed',
    image_url VARCHAR(500),
    detection_count INT DEFAULT 0,
    process_duration_ms INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 检测结果表
CREATE TABLE IF NOT EXISTS detection_results (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    record_id BIGINT NOT NULL,
    object_id VARCHAR(50),
    object_type VARCHAR(30),
    bbox_x1 FLOAT,
    bbox_y1 FLOAT,
    bbox_x2 FLOAT,
    bbox_y2 FLOAT,
    confidence FLOAT,
    result_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (record_id) REFERENCES inference_records(id)
);

-- 异步任务表
CREATE TABLE IF NOT EXISTS jobs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    job_id VARCHAR(50) NOT NULL UNIQUE,
    task_type VARCHAR(30) NOT NULL,
    status VARCHAR(20) DEFAULT 'queued',
    progress INT DEFAULT 0,
    processed_frames INT DEFAULT 0,
    total_frames INT DEFAULT 0,
    input_url VARCHAR(500),
    options_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 告警事件表
CREATE TABLE IF NOT EXISTS alert_events (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    alert_id VARCHAR(50) NOT NULL UNIQUE,
    severity VARCHAR(20) NOT NULL,
    title VARCHAR(200),
    summary TEXT,
    anomaly_type VARCHAR(50),
    affected_module VARCHAR(50),
    metrics_json TEXT,
    suggested_actions TEXT,
    status VARCHAR(20) DEFAULT 'open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
);

-- 系统日志表
CREATE TABLE IF NOT EXISTS system_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    level VARCHAR(10) NOT NULL,
    module VARCHAR(50),
    event VARCHAR(100),
    detail_json TEXT,
    trace_id VARCHAR(50)
);
