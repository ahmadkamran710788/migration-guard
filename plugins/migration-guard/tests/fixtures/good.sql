-- migrate:up
ALTER TABLE users ADD COLUMN plan text;
CREATE INDEX CONCURRENTLY idx_users_plan ON users (plan);
ALTER TABLE users ADD CONSTRAINT fk_users_org FOREIGN KEY (org_id) REFERENCES orgs(id) NOT VALID;
-- migrate:down
DROP INDEX CONCURRENTLY idx_users_plan;
ALTER TABLE users DROP CONSTRAINT fk_users_org;
