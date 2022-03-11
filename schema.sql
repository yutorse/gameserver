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
  PRIMARY KEY (`room_id`)
);

DROP TABLE IF EXISTS `room_members`;
CREATE TABLE `room_members` (
  `token` varchar(255) NOT NULL,
  `room_id` bigint NOT NULL,
  `select_difficulty` int DEFAULT NULL,
  PRIMARY KEY (`token`, `room_id`),
  UNIQUE KEY `token` (`token`)
);