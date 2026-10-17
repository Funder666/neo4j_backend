-- Upgrade an existing running user_neo4j table for registration review.
-- Safe to run repeatedly on the same database.
-- Usage:
--   mysql -uroot -p123456 -h127.0.0.1 -P3306 -D neo4j < upgrade_existing_user_registration_review.sql
--
-- Do not run create_users_table.sql on an existing production database.

ALTER TABLE user_neo4j
    MODIFY email VARCHAR(100) NULL COMMENT '邮箱地址',
    MODIFY status ENUM('pending', 'active', 'inactive', 'suspended', 'rejected') DEFAULT 'pending' COMMENT '用户状态';

DROP PROCEDURE IF EXISTS add_user_column_if_missing;

DELIMITER //
CREATE PROCEDURE add_user_column_if_missing(
    IN column_name VARCHAR(64),
    IN column_definition TEXT
)
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'user_neo4j'
          AND COLUMN_NAME = column_name
    ) THEN
        SET @alter_sql = CONCAT('ALTER TABLE user_neo4j ADD COLUMN ', column_definition);
        PREPARE alter_stmt FROM @alter_sql;
        EXECUTE alter_stmt;
        DEALLOCATE PREPARE alter_stmt;
    END IF;
END//
DELIMITER ;

CALL add_user_column_if_missing('institution', 'institution VARCHAR(200) COMMENT ''所在机构''');
CALL add_user_column_if_missing('identity_type', 'identity_type VARCHAR(50) COMMENT ''身份类型''');
CALL add_user_column_if_missing('application_purpose', 'application_purpose TEXT COMMENT ''申请账号目的''');
CALL add_user_column_if_missing('country_region', 'country_region VARCHAR(100) COMMENT ''所属国家和地区''');
CALL add_user_column_if_missing('phone', 'phone VARCHAR(20) COMMENT ''手机号码''');
CALL add_user_column_if_missing('reviewed_by', 'reviewed_by INT COMMENT ''审核人ID''');
CALL add_user_column_if_missing('reviewed_at', 'reviewed_at DATETIME COMMENT ''审核时间''');
CALL add_user_column_if_missing('review_reason', 'review_reason TEXT COMMENT ''审核不通过理由''');

DROP PROCEDURE IF EXISTS add_user_column_if_missing;
