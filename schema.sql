DROP TABLE IF EXISTS `user`;
CREATE TABLE `user` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(255) DEFAULT NULL,
  `token` varchar(255) DEFAULT NULL,
  `leader_card_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `token` (`token`)
);

DROP TABLE IF EXISTS `room`;
CREATE TABLE `room` (
  `room_id` bigint NOT NULL AUTO_INCREMENT,
  `live_id` int NOT NULL,
  `joined_user_count` int DEFAULT NULL,
  `status` int DEFAULT 1, -- 入場OK -> 1, 満員 -> 2, 解散済み -> 3
  `host` bigint NOT NULL,
  PRIMARY KEY (`room_id`)
);

DROP TABLE IF EXISTS `room_members`;
CREATE TABLE `room_members` (
  `room_id` bigint NOT NULL,
  `user_id` bigint NOT NULL,
  `select_difficulty` int DEFAULT NULL,
  `status` int DEFAULT 1, -- プレイ終了前 -> 1, プレイ終了後 -> 2
  `score` int DEFAULT NULL,
  `perfect` int DEFAULT NULL,
  `great` int DEFAULT NULL,
  `good` int DEFAULT NULL,
  `bad` int DEFAULT NULL,
  `miss` int DEFAULT NULL,
  `token` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`room_id`, `user_id`),
  FOREIGN KEY `room_id` (`room_id`) REFERENCES `room` (`room_id`) ON DELETE CASCADE,
  FOREIGN KEY `user_id` (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
);