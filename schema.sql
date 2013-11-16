CREATE TYPE user_class AS ENUM ('Tenant', 'Landlord', 'Both');
CREATE TYPE issue_status AS ENUM ('Open', 'Closed', 'Pending');
CREATE TYPE issue_severity AS ENUM ('Critical', 'Medium', 'Low', 'Future');
CREATE TYPE code_types AS ENUM ('verify', 'reset')
CREATE TYPE email_types AS ENUM ('verify',
                                'reset',
                                'issue',
                                'comment',
                                'relation',
                                'payment')

CREATE TABLE users (
    id              serial primary key,
    username        text NOT NULL UNIQUE,
    email           text NOT NULL UNIQUE,
    password        text NOT NULL,
    category        user_class NOT NULL,
    verified        boolean NOT NULL DEFAULT FALSE,
    accepts_cc      boolean NOT NULL DEFAULT FALSE,
    joined          timestamp NOT NULL DEFAULT current_timestamp
);

CREATE TABLE agreements (
    id              serial primary key,
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

CREATE TABLE failed_logins (
    account         text NOT NULL,
    ip              inet NOT NULL,
    time            timestamp NOT NULL DEFAULT current_timestamp
);

CREATE TABLE failed_emails (
    ip              inet NOT NULL,
    time            timestamp NOT NULL DEFAULT current_timestamp
);

CREATE TABLE sent_emails (
    account         integer references users (id) NOT NULL,
    ip              inet NOT NULL,
    type            email_types NOT NULL,
    time            timestamp NOT NULL DEFAULT current_timestamp
);

CREATE TABLE payments (
    id              serial NOT NULL primary key,
    stripe_id       text NOT NULL,
    from_user       integer references users (id) NOT NULL,
    to_user         integer references users (id) NOT NULL,
    time            timestamp NOT NULL DEFAULT current_timestamp
);

CREATE TABLE user_keys (
    id              serial NOT NULL primary key,
    user_id         integer references users(id) NOT NULL UNIQUE,
    pub_key         text NOT NULL,
    sec_key         text NOT NULL,
    refresh_token   text NOT NULL,
    retrieved       timestamp NOT NULL DEFAULT current_timestamp
);

CREATE TABLE codes (
    user_id         integer references users(id) NOT NULL,
    type            code_types NOT NULL,
    value           text NOT NULL,
    created         timestamp NOT NULL DEFAULT current_timestamp
);

CREATE TABLE properties (
    id              serial primary key,
    location        text NOT NULL,
    owner           integer references users(id) NOT NULL,
    description     text
);

CREATE TABLE relations (
    tenant          integer references users(id) NOT NULL,
    landlord        integer references users(id) NOT NULL,
    started         timestamp NOT NULL DEFAULT current_timestamp,
    location        integer references properties(id) NOT NULL,
    confirmed       boolean NOT NULL DEFAULT FALSE,
    stopped         timestamp,
    unique (tenant, landlord, location)
);

CREATE TABLE issues (
    id              serial primary key,
    owner           integer references users(id) NOT NULL,
    creator         integer references users(id) NOT NULL,
    location        integer references properties(id) NOT NULL,
    description     text NOT NULL,
    severity        issue_severity NOT NULL,
    status          issue_status NOT NULL,
    opened          timestamp NOT NULL DEFAULT current_timestamp,
    closed          timestamp
);

CREATE TABLE comments (
    id              serial primary key,
    user_id         integer references users(id) NOT NULL,
    issue_id        integer references issues(id) NOT NULL,
    text            text NOT NULL,
    posted          timestamp NOT NULL DEFAULT current_timestamp
);
