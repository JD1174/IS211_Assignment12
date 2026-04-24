DROP TABLE IF EXISTS students;
DROP TABLE IF EXISTS quizzes;
DROP TABLE IF EXISTS results;

CREATE TABLE students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL
);

CREATE TABLE quizzes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL,
    num_questions INTEGER NOT NULL,
    quiz_date TEXT NOT NULL
);

CREATE TABLE results (
    student_id INTEGER NOT NULL,
    quiz_id INTEGER NOT NULL,
    score INTEGER NOT NULL,
    PRIMARY KEY (student_id, quiz_id),
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE
);

-- Load initial test data for debugging purposes
INSERT INTO students (first_name, last_name) VALUES ('John', 'Smith');
INSERT INTO quizzes (subject, num_questions, quiz_date) VALUES ('Python Basics', 5, '2015-02-05');
INSERT INTO results (student_id, quiz_id, score) VALUES (1, 1, 85);