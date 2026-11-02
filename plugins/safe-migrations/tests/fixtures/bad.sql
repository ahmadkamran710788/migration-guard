-- migrate:up
ALTER TABLE users ADD COLUMN plan text NOT NULL;
CREATE INDEX idx_users_plan ON users (plan);
ALTER TABLE users ADD CONSTRAINT fk_users_org FOREIGN KEY (org_id) REFERENCES orgs(id);
DROP TABLE legacy_sessions;
UPDATE users SET plan = 'free';
