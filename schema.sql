CREATE TABLE users (
    id              serial NOT NULL primary key,
    email           text NOT NULL,
    password        text NOT NULL,
    privilege       integer NOT NULL DEFAULT 0,
    joined          timestamp NOT NULL DEFAULT current_timestamp
);

CREATE TABLE agreements (
    id              serial NOT NULL primary key,
    user_id         integer references users (id) NOT NULL,
    landlord        integer references users (id),
    file_name       text NOT NULL,
    data_type       text NOT NULL,
    data            text NOT NULL,
    title           text,
    description     text,
    posted_on       timestamp NOT NULL DEFAULT current_timestamp
);

CREATE TABLE sessions (
    session_id      char(128) UNIQUE NOT NULL,
    atime           timestamp NOT NULL DEFAULT current_timestamp,
    data            text
);
