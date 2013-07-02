CREATE TABLE agreements (
    id              SERIAL NOT NULL PRIMARY KEY,
    user            INTEGER REFERENCES users(id) NOT NULL,
    landlord        INTEGER REFERENCES users(id),
    title           TEXT,
    description     TEXT,
    posted_on       DATETIME NOT NULL,
);

CREATE TABLE users (
    id              SERIAL NOT NULL PRIMARY KEY,
    email           TEXT NOT NULL,
    pwd             TEXT NOT NULL,
    privilege       INTEGER NOT NULL DEFAULT 0,
    joined          DATETIME NOT NULL,
);
