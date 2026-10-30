CREATE TABLE IF NOT EXISTS places (
 id INTEGER PRIMARY KEY,
 region TEXT NOT NULL,
 city TEXT NOT NULL,
 name TEXT NOT NULL,
 category TEXT NOT NULL CHECK(category IN ('stay','scenery','food')),
 audience TEXT NOT NULL CHECK(audience IN ('family','solo','both')),
 description TEXT NOT NULL,
 tags TEXT NOT NULL,
 source_url TEXT,
 checked_at TEXT,
 operating_status TEXT NOT NULL DEFAULT '미확인',
 is_demo INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_places_filter ON places(region, category, audience);
