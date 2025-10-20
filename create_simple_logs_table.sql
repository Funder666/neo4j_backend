-- 简化的查询日志表（单表设计）
CREATE TABLE query_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    -- 用户信息
    user_id INT NOT NULL COMMENT '用户ID',
    user_role VARCHAR(20) COMMENT '用户角色',
    ip_address VARCHAR(45) COMMENT '用户IP地址',

    -- 查询信息
    query_type ENUM('node_query', 'relationship_query', 'cypher_query', 'smart_query') NOT NULL COMMENT '查询类型',
    page_name VARCHAR(50) NOT NULL COMMENT '页面名称',
    query_content TEXT COMMENT '查询内容（节点名称、关系类型、Cypher语句等）',
    cypher_query TEXT COMMENT '实际执行的Cypher查询语句',

    -- 智能查询特有字段
    natural_language_query TEXT COMMENT '用户输入的自然语言查询',
    generated_cypher TEXT COMMENT 'AI生成的Cypher查询',
    satisfaction_rating ENUM('satisfied', 'unsatisfied') COMMENT '用户满意度评价',

    -- 执行结果信息
    execution_status ENUM('success', 'error') NOT NULL COMMENT '执行状态',
    result_count INT DEFAULT 0 COMMENT '返回结果数量',
    node_count INT DEFAULT 0 COMMENT '节点数量',
    edge_count INT DEFAULT 0 COMMENT '边数量',
    execution_time_ms BIGINT COMMENT '执行时间（毫秒）',
    error_message TEXT COMMENT '错误信息',

    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    -- 索引
    INDEX idx_user_id (user_id),
    INDEX idx_user_role (user_role),
    INDEX idx_query_type (query_type),
    INDEX idx_created_at (created_at),
    INDEX idx_execution_status (execution_status),
    INDEX idx_page_name (page_name),
    INDEX idx_ip_address (ip_address)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='查询操作日志表';