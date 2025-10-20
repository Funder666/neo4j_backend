-- 标签映射和权限控制表结构设计

-- 1. 标签映射表 - 存储Neo4j标签到显示名称的映射
CREATE TABLE IF NOT EXISTS label_mappings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    type ENUM('node', 'relationship') NOT NULL COMMENT '类型：node-节点标签，relationship-关系标签',
    neo4j_name VARCHAR(100) NOT NULL COMMENT 'Neo4j中的原始标签名',
    display_name VARCHAR(100) NOT NULL COMMENT '显示给用户的中文名称',
    description TEXT COMMENT '标签描述',
    sort_order INT DEFAULT 0 COMMENT '排序顺序',
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    UNIQUE KEY uk_type_neo4j_name (type, neo4j_name),
    INDEX idx_type (type),
    INDEX idx_neo4j_name (neo4j_name),
    INDEX idx_display_name (display_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='标签映射表';

-- 2. 用户角色权限表 - 控制不同用户角色能看到哪些标签
CREATE TABLE IF NOT EXISTS user_label_permissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_role VARCHAR(50) NOT NULL COMMENT '用户角色',
    label_mapping_id INT NOT NULL COMMENT '标签映射ID',
    can_view BOOLEAN DEFAULT TRUE COMMENT '是否可以查看',
    can_create BOOLEAN DEFAULT FALSE COMMENT '是否可以创建',
    can_edit BOOLEAN DEFAULT FALSE COMMENT '是否可以编辑',
    can_delete BOOLEAN DEFAULT FALSE COMMENT '是否可以删除',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    FOREIGN KEY (label_mapping_id) REFERENCES label_mappings(id) ON DELETE CASCADE,
    UNIQUE KEY uk_role_label (user_role, label_mapping_id),
    INDEX idx_user_role (user_role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户标签权限表';

-- 3. 标签属性表 - 定义节点/关系的属性显示信息
CREATE TABLE IF NOT EXISTS label_properties (
    id INT AUTO_INCREMENT PRIMARY KEY,
    label_mapping_id INT NOT NULL COMMENT '关联的标签映射ID',
    property_key VARCHAR(100) NOT NULL COMMENT '属性键名',
    display_name VARCHAR(100) NOT NULL COMMENT '属性显示名称',
    description TEXT COMMENT '属性描述',
    data_type VARCHAR(50) DEFAULT 'string' COMMENT '数据类型：string, number, boolean, date等',
    sort_order INT DEFAULT 0 COMMENT '显示顺序',
    is_display BOOLEAN DEFAULT TRUE COMMENT '是否在前端显示',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    FOREIGN KEY (label_mapping_id) REFERENCES label_mappings(id) ON DELETE CASCADE,
    UNIQUE KEY uk_label_property (label_mapping_id, property_key),
    INDEX idx_label_mapping_id (label_mapping_id),
    INDEX idx_property_key (property_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='标签属性表';

-- 插入基础数据

-- -- 节点标签映射
-- INSERT INTO label_mappings (type, neo4j_name, display_name, description, sort_order) VALUES
-- ('node', 'Character', '汉字', '中文汉字字符', 1),
-- ('node', 'Radical', '部首', '汉字的部首组成部分', 2),
-- ('node', 'Pinyin', '拼音', '汉字的拼音标注', 3),
-- ('node', 'Word', '词语', '由汉字组成的词汇', 4);
--
-- -- 关系标签映射
-- INSERT INTO label_mappings (type, neo4j_name, display_name, description, sort_order) VALUES
-- ('relationship', 'SYNONYM', '近义词', '表示两个词语意思相近', 1),
-- ('relationship', 'HAS_PINYIN', '汉字与拼音', '汉字对应的拼音读音', 2),
-- ('relationship', 'HAS_RADICAL', '汉字与部首', '汉字包含的部首结构', 3),
-- ('relationship', 'ANTONYM', '反义词', '表示两个词语意思相反', 4),
-- ('relationship', 'DEPENDS_ON', '学习依赖', '汉字学习的先后依赖关系', 5);

-- 管理员角色权限（管理员可以查看和操作所有标签）
INSERT INTO user_label_permissions (user_role, label_mapping_id, can_view, can_create, can_edit, can_delete)
SELECT 'admin', id, TRUE, TRUE, TRUE, TRUE FROM label_mappings;

-- user权限（user可以查看所有标签）
INSERT INTO user_label_permissions (user_role, label_mapping_id, can_view, can_create, can_edit, can_delete)
SELECT 'user', id, TRUE, False, False, False FROM label_mappings;

-- user1权限：可以访问标签ID为1的标签（Character）和所有关系标签（ID 5-9）
INSERT INTO user_label_permissions (user_role, label_mapping_id, can_view, can_create, can_edit, can_delete) VALUES
('user1', 1, TRUE, TRUE, TRUE, TRUE); -- Character标签

-- user2权限：可以访问标签ID为2的标签（Radical）和所有关系标签（ID 5-9）
INSERT INTO user_label_permissions (user_role, label_mapping_id, can_view, can_create, can_edit, can_delete) VALUES
('user2', 2, TRUE, TRUE, TRUE, TRUE); -- Radical标签

-- user3权限：可以访问标签ID为3的标签（Pinyin）和所有关系标签（ID 5-9）
INSERT INTO user_label_permissions (user_role, label_mapping_id, can_view, can_create, can_edit, can_delete) VALUES
('user3', 3, TRUE, TRUE, TRUE, TRUE);  -- Pinyin标签

-- user4权限：可以访问标签ID为4的标签（Word）和所有关系标签（ID 5-9）
INSERT INTO user_label_permissions (user_role, label_mapping_id, can_view, can_create, can_edit, can_delete) VALUES
('user4', 4, TRUE, TRUE, TRUE, TRUE);  -- Word标签

-- Character节点的属性设置（基于实际属性：animation_url, definition, guide_url, hskLevel, meaning, name, newStandardLevel, pinyin, stroke_url, strokes, value）
INSERT INTO label_properties (label_mapping_id, property_key, display_name, description, data_type, sort_order) VALUES
((SELECT id FROM label_mappings WHERE neo4j_name = 'Character'), 'name', '汉字名称', '汉字的标准名称', 'string', 1),
((SELECT id FROM label_mappings WHERE neo4j_name = 'Character'), 'value', '汉字内容', '汉字字符值', 'string', 2),
((SELECT id FROM label_mappings WHERE neo4j_name = 'Character'), 'meaning', '汉字释义', '汉字的含义解释', 'text', 3),
((SELECT id FROM label_mappings WHERE neo4j_name = 'Character'), 'definition', '汉字定义', '汉字的详细定义', 'text', 4),
((SELECT id FROM label_mappings WHERE neo4j_name = 'Character'), 'pinyin', '拼音读音', '汉字的拼音标注', 'string', 5),
((SELECT id FROM label_mappings WHERE neo4j_name = 'Character'), 'strokes', '笔画数', '汉字总笔画数', 'number', 6),
((SELECT id FROM label_mappings WHERE neo4j_name = 'Character'), 'hskLevel', 'HSK等级', '汉语水平考试等级', 'number', 7),
((SELECT id FROM label_mappings WHERE neo4j_name = 'Character'), 'newStandardLevel', '新标准等级', '新课程标准等级', 'number', 8),
((SELECT id FROM label_mappings WHERE neo4j_name = 'Character'), 'animation_url', '动画链接', '汉字书写动画URL', 'string', 9),
((SELECT id FROM label_mappings WHERE neo4j_name = 'Character'), 'guide_url', '指导链接', '学习指导资源URL', 'string', 10),
((SELECT id FROM label_mappings WHERE neo4j_name = 'Character'), 'stroke_url', '笔顺链接', '笔画顺序图片URL', 'string', 11);

-- Pinyin节点的属性设置（基于实际属性：audio_url, mysql_id, name, value, tone）
INSERT INTO label_properties (label_mapping_id, property_key, display_name, description, data_type, sort_order, is_display) VALUES
((SELECT id FROM label_mappings WHERE neo4j_name = 'Pinyin'), 'name', '拼音名称', '拼音标识名称', 'string', 1, TRUE),
((SELECT id FROM label_mappings WHERE neo4j_name = 'Pinyin'), 'value', '拼音内容', '拼音字符值', 'string', 2, TRUE),
((SELECT id FROM label_mappings WHERE neo4j_name = 'Pinyin'), 'tone', '声调', '拼音声调（1-4）', 'number', 3, TRUE),
((SELECT id FROM label_mappings WHERE neo4j_name = 'Pinyin'), 'audio_url', '音频链接', '拼音发音音频URL', 'string', 4, TRUE),
((SELECT id FROM label_mappings WHERE neo4j_name = 'Pinyin'), 'mysql_id', 'MySQL ID', 'MySQL数据库中的ID', 'number', 5, FALSE); -- 不在前端显示MySQL ID

-- Word节点的属性设置（基于实际属性：antonyms, synonyms, hskLevel, newStandardLevel, mysql_id, name, value）
INSERT INTO label_properties (label_mapping_id, property_key, display_name, description, data_type, sort_order, is_display) VALUES
((SELECT id FROM label_mappings WHERE neo4j_name = 'Word'), 'name', '词语名称', '词语标识名称', 'string', 1, TRUE),
((SELECT id FROM label_mappings WHERE neo4j_name = 'Word'), 'value', '词语内容', '词语字符值', 'string', 2, TRUE),
((SELECT id FROM label_mappings WHERE neo4j_name = 'Word'), 'synonyms', '近义词', '同义词列表', 'text', 3, TRUE),
((SELECT id FROM label_mappings WHERE neo4j_name = 'Word'), 'antonyms', '反义词', '反义词列表', 'text', 4, TRUE),
((SELECT id FROM label_mappings WHERE neo4j_name = 'Word'), 'hskLevel', 'HSK等级', '汉语水平考试等级', 'number', 5, TRUE),
((SELECT id FROM label_mappings WHERE neo4j_name = 'Word'), 'newStandardLevel', '新标准等级', '新课程标准等级', 'number', 6, TRUE),
((SELECT id FROM label_mappings WHERE neo4j_name = 'Word'), 'mysql_id', 'MySQL ID', 'MySQL数据库中的ID', 'number', 7, FALSE); -- 不在前端显示MySQL ID

-- Radical节点的属性设置（基于实际属性：value）
INSERT INTO label_properties (label_mapping_id, property_key, display_name, description, data_type, sort_order) VALUES
((SELECT id FROM label_mappings WHERE neo4j_name = 'Radical'), 'value', '部首内容', '部首字符值', 'string', 1);


