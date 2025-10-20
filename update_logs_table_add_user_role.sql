- 为现有的日志记录表添加用户角色字段
-- 如果表已经存在，使用以下ALTER语句添加user_role字段

-- 为query_logs表添加user_role字段
ALTER TABLE query_logs ADD COLUMN user_role VARCHAR(20) COMMENT '用户角色' AFTER user_id;

-- 为user_behavior_logs表添加user_role字段
ALTER TABLE user_behavior_logs ADD COLUMN user_role VARCHAR(20) COMMENT '用户角色' AFTER user_id;

-- 可选：为user_role字段添加索引以提高查询性能
ALTER TABLE query_logs ADD INDEX idx_user_role (user_role);
ALTER TABLE user_behavior_logs ADD INDEX idx_user_role (user_role);

-- 可选：更新现有记录的user_role（如果需要的话）
-- UPDATE query_logs q
-- JOIN user_neo4j u ON q.user_id = u.id
-- SET q.user_role = u.role
-- WHERE q.user_role IS NULL;

-- UPDATE user_behavior_logs b
-- JOIN user_neo4j u ON b.user_id = u.id
-- SET b.user_role = u.role
-- WHERE b.user_role IS NULL;