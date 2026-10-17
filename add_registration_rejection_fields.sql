-- Add rejection status and rejection reason for registration review.

ALTER TABLE user_neo4j
    MODIFY status ENUM('pending', 'active', 'inactive', 'suspended', 'rejected') DEFAULT 'pending' COMMENT '用户状态';

SET @sql = (
    SELECT IF(
        COUNT(*) = 0,
        'ALTER TABLE user_neo4j ADD COLUMN review_reason TEXT COMMENT ''审核不通过理由''',
        'SELECT ''review_reason already exists'''
    )
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'user_neo4j' AND COLUMN_NAME = 'review_reason'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
