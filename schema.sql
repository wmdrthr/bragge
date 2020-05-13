
CREATE TABLE genres (
       id SERIAL PRIMARY KEY,
       genre VARCHAR(10) NOT NULL UNIQUE
);

INSERT INTO genres (genre) VALUES ('Culture');
INSERT INTO genres (genre) VALUES ('History');
INSERT INTO genres (genre) VALUES ('Philosophy');
INSERT INTO genres (genre) VALUES ('Religion');
INSERT INTO genres (genre) VALUES ('Science');

CREATE TABLE eras (
       id SERIAL PRIMARY KEY,
       era VARCHAR(18) NOT NULL UNIQUE
);

INSERT INTO eras (era) VALUES ('Prehistoric');
INSERT INTO eras (era) VALUES ('Mesopotamian');
INSERT INTO eras (era) VALUES ('Ancient Egypt');
INSERT INTO eras (era) VALUES ('Ancient Greece');
INSERT INTO eras (era) VALUES ('Ancient Rome');
INSERT INTO eras (era) VALUES ('Early Middle Ages');
INSERT INTO eras (era) VALUES ('Medieval');
INSERT INTO eras (era) VALUES ('Renaissance');
INSERT INTO eras (era) VALUES ('16th Century');
INSERT INTO eras (era) VALUES ('17th Century');
INSERT INTO eras (era) VALUES ('18th Century');
INSERT INTO eras (era) VALUES ('Enlightenment');
INSERT INTO eras (era) VALUES ('Romantic');
INSERT INTO eras (era) VALUES ('19th Century');
INSERT INTO eras (era) VALUES ('Victorian');
INSERT INTO eras (era) VALUES ('20th Century');

CREATE TABLE episodes (
       id SERIAL PRIMARY KEY,
       slug VARCHAR(12) NOT NULL UNIQUE,
       title VARCHAR(256) NOT NULL,
       date TIMESTAMP NOT NULL,
       parsed_at TIMESTAMP NOT NULL,
       url TEXT NOT NULL,
       synopsis TEXT,
       genre INTEGER REFERENCES genres(id),
       era INTEGER REFERENCES eras(id)
);

CREATE INDEX episodes_slugs_index ON episodes (slug);

CREATE TABLE descriptions (
       id SERIAL PRIMARY KEY,
       episodeid INTEGER REFERENCES episodes(id),
       description TEXT NOT NULL
);

CREATE TABLE links (
       id SERIAL PRIMARY KEY,
       episodeid INTEGER REFERENCES episodes(id),
       link_text TEXT NOT NULL
);

CREATE TABLE reading_lists (
       id SERIAL PRIMARY KEY,
       episodeid INTEGER REFERENCES episodes(id),
       rl_entry TEXT NOT NULL
);
