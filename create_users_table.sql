-- 创建用户表
CREATE TABLE IF NOT EXISTS user_neo4j (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL COMMENT '用户名',
    email VARCHAR(100) UNIQUE NOT NULL COMMENT '邮箱地址',
    password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希',
    full_name VARCHAR(100) COMMENT '真实姓名',
    role VARCHAR(50) DEFAULT 'user' COMMENT '用户角色，支持扩展',
    status ENUM('active', 'inactive', 'suspended') DEFAULT 'active' COMMENT '用户状态',
    avatar_url VARCHAR(500) COMMENT '头像URL',
    phone VARCHAR(20) COMMENT '手机号码',
    department VARCHAR(100) COMMENT '部门',
    position VARCHAR(100) COMMENT '职位',
    last_login DATETIME COMMENT '最后登录时间',
    login_count INT DEFAULT 0 COMMENT '登录次数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    created_by INT COMMENT '创建人ID',
    INDEX idx_username (username),
    INDEX idx_email (email),
    INDEX idx_role (role),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Neo4j用户表';

-- 插入默认管理员用户
-- 注意：密码hash需要在运行时生成，这里提供示例
-- admin用户密码: admin
-- neo4j用户密码: admin
INSERT INTO user_neo4j (username, email, password_hash, full_name, role, status) VALUES 
('admin', 'admin@example.com', '$2b$12$rUi4pOWR6FEfXDNubPuD5eONlI4dMVeBh61ASzaIcsJR1fl76k6h2', '系统管理员', 'admin', 'active'),
('neo4j', 'neo4j@example.com', '$2b$12$Pom3jJ3Zp8PUMX5PhoSFouGXg1O3UlD.AJMBM/jVig3YYjHEQrueW', 'Neo4j用户', 'user', 'active');

-- 插入新的用户角色数据（密码已使用bcrypt哈希）
-- user1-user4用户密码分别为各自的用户名
INSERT INTO user_neo4j (username, email, password_hash, full_name, role, status, created_at) VALUES
('user1', 'user1@example.com', '$2b$12$2UphBuaWkthjxKqHvSfgw.ZmscoFLJtai5VS7LL2pP5nitl7Bhi0a', '汉字管理员', 'user1', 'active', NOW()),
('user2', 'user2@example.com', '$2b$12$NPDLvLkmJW5JnDBCJp3RzOJ5x0pfsEwxh6lhZDzDRaXOIMIImhWla', '部首管理员', 'user2', 'active', NOW()),
('user3', 'user3@example.com', '$2b$12$qvsYcTK7gRLCkFi7Xs3xyOkFALOIo/GHMebGAYAU./LGUX2aj6RDO', '拼音管理员', 'user3', 'active', NOW()),
('user4', 'user4@example.com', '$2b$12$s0oZ7s.ejyEo0iBvcrselu3iRYMAZbRF77QIpbgSr6jMLZJoPmERS', '词语管理员', 'user4', 'active', NOW());