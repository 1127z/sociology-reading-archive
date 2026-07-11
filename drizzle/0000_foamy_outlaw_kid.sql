CREATE TABLE `articles` (
	`slug` text PRIMARY KEY NOT NULL,
	`date` text NOT NULL,
	`issue` text NOT NULL,
	`title` text NOT NULL,
	`title_en` text NOT NULL,
	`authors` text NOT NULL,
	`journal` text NOT NULL,
	`method` text NOT NULL,
	`topics` text NOT NULL,
	`source_url` text NOT NULL,
	`document_url` text NOT NULL,
	`payload` text NOT NULL,
	`created_at` integer DEFAULT (unixepoch() * 1000) NOT NULL
);
--> statement-breakpoint
CREATE INDEX `articles_date_idx` ON `articles` (`date`);--> statement-breakpoint
CREATE INDEX `articles_method_idx` ON `articles` (`method`);--> statement-breakpoint
CREATE TABLE `reading_progress` (
	`user_key` text NOT NULL,
	`article_slug` text NOT NULL,
	`status` text DEFAULT 'unread' NOT NULL,
	`note` text DEFAULT '' NOT NULL,
	`updated_at` integer DEFAULT (unixepoch() * 1000) NOT NULL,
	PRIMARY KEY(`user_key`, `article_slug`),
	FOREIGN KEY (`article_slug`) REFERENCES `articles`(`slug`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE INDEX `progress_user_idx` ON `reading_progress` (`user_key`);