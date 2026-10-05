CREATE TABLE IF NOT EXISTS `groups` (
	`id` text PRIMARY KEY NOT NULL,
	`code` text NOT NULL,
	`name` text NOT NULL,
	`created` integer NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX IF NOT EXISTS `groups_code_unique` ON `groups` (`code`);--> statement-breakpoint
CREATE TABLE IF NOT EXISTS `messages` (
	`id` text PRIMARY KEY NOT NULL,
	`gid` text NOT NULL,
	`sender` text NOT NULL,
	`channel` text NOT NULL,
	`target` text,
	`body` text NOT NULL,
	`reply` text,
	`created` integer NOT NULL,
	`deleted` integer DEFAULT 0 NOT NULL,
	FOREIGN KEY (`gid`) REFERENCES `groups`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`sender`) REFERENCES `sessions`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE INDEX IF NOT EXISTS `idx_messages_gid_created` ON `messages` (`gid`,`created`);--> statement-breakpoint
CREATE TABLE IF NOT EXISTS `reactions` (
	`mid` text NOT NULL,
	`uid` text NOT NULL,
	`emoji` text NOT NULL,
	PRIMARY KEY(`mid`, `uid`, `emoji`),
	FOREIGN KEY (`mid`) REFERENCES `messages`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`uid`) REFERENCES `sessions`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS `sessions` (
	`id` text PRIMARY KEY NOT NULL,
	`token` text NOT NULL,
	`gid` text NOT NULL,
	`name` text NOT NULL,
	`avatar` text NOT NULL,
	`color` text NOT NULL,
	`seen` integer NOT NULL,
	`typing` integer DEFAULT 0 NOT NULL,
	`channel` text DEFAULT 'geral' NOT NULL,
	`expires` integer NOT NULL,
	`last_sent` integer DEFAULT 0 NOT NULL,
	FOREIGN KEY (`gid`) REFERENCES `groups`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE UNIQUE INDEX IF NOT EXISTS `sessions_token_unique` ON `sessions` (`token`);--> statement-breakpoint
CREATE INDEX IF NOT EXISTS `idx_sessions_gid_seen` ON `sessions` (`gid`,`seen`);