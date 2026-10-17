-- Add public registration and administrator review fields.

ALTER TABLE user_neo4j
    MODIFY email VARCHAR(100) NULL COMMENT '邮箱地址',
    MODIFY status ENUM('pending', 'active', 'inactive', 'suspended', 'rejected') DEFAULT 'pending' COMMENT '用户状态';

SET @sql = (
    SELECT IF(
        COUNT(*) = 0,
        'ALTER TABLE user_neo4j ADD COLUMN institution VARCHAR(200) COMMENT ''所在机构''',
        'SELECT ''institution already exists'''
    )
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'user_neo4j' AND COLUMN_NAME = 'institution'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT IF(
        COUNT(*) = 0,
        'ALTER TABLE user_neo4j ADD COLUMN identity_type VARCHAR(50) COMMENT ''身份类型''',
        'SELECT ''identity_type already exists'''
    )
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'user_neo4j' AND COLUMN_NAME = 'identity_type'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT IF(
        COUNT(*) = 0,
        'ALTER TABLE user_neo4j ADD COLUMN application_purpose TEXT COMMENT ''申请账号目的''',
        'SELECT ''application_purpose already exists'''
    )
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'user_neo4j' AND COLUMN_NAME = 'application_purpose'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT IF(
        COUNT(*) = 0,
        'ALTER TABLE user_neo4j ADD COLUMN country_region VARCHAR(100) COMMENT ''所属国家和地区''',
        'SELECT ''country_region already exists'''
    )
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'user_neo4j' AND COLUMN_NAME = 'country_region'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT IF(
        COUNT(*) = 0,
        'ALTER TABLE user_neo4j ADD COLUMN reviewed_by INT COMMENT ''审核人ID''',
        'SELECT ''reviewed_by already exists'''
    )
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'user_neo4j' AND COLUMN_NAME = 'reviewed_by'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT IF(
        COUNT(*) = 0,
        'ALTER TABLE user_neo4j ADD COLUMN reviewed_at DATETIME COMMENT ''审核时间''',
        'SELECT ''reviewed_at already exists'''
    )
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'user_neo4j' AND COLUMN_NAME = 'reviewed_at'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

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
