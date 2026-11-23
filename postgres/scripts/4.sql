-- Перевірка тригерів цілісності.
-- Запуск у psql (база hotel):   \i /pg/4.sql
--
-- Кожне правило показано двома боками: порушення блокується помилкою, а коректна
-- дія виконується. Тестові зміни наприкінці скасовуються, тож скрипт можна
-- запускати скільки завгодно разів.

\pset pager off
\set VERBOSITY terse
\set ECHO queries

\echo
\echo '=== Правило 1. Місткість номера ==='
\echo '1а. Номер 101 одномісний і вже зайнятий: заселення відхиляється'
INSERT INTO stays (client_id, room_id, checkin_date)
SELECT c.client_id, r.room_id, CURRENT_DATE
FROM clients c, rooms r
WHERE c.passport_number = 'ЕК789012' AND r.room_number = 101;

\echo '1б. Номер 201 двомісний, зайнято 1 місце: заселення можливе'
INSERT INTO stays (client_id, room_id, checkin_date)
SELECT c.client_id, r.room_id, CURRENT_DATE
FROM clients c, rooms r
WHERE c.passport_number = 'ЕК789012' AND r.room_number = 201;

\echo '1в. Тепер 201 заповнений (2 з 2): ще одне заселення відхиляється'
INSERT INTO stays (client_id, room_id, checkin_date)
SELECT c.client_id, r.room_id, CURRENT_DATE
FROM clients c, rooms r
WHERE c.passport_number = 'ЕК567890' AND r.room_number = 201;


\echo
\echo '=== Правило 1 (продовження). Зміна типів не повинна порушувати місткість ==='
\echo 'У 201 живуть двоє. Зменшити місткість двомісних номерів до 1 не можна:'
UPDATE room_types SET capacity = 1 WHERE name = 'двомісний';

\echo 'Зробити номер 201 одномісним теж не можна:'
UPDATE rooms
SET room_type_id = (SELECT room_type_id FROM room_types WHERE name = 'одномісний')
WHERE room_number = 201;

\echo 'Тестове заселення в 201 прибираємо:'
DELETE FROM stays
WHERE client_id = (SELECT client_id FROM clients WHERE passport_number = 'ЕК789012')
  AND room_id   = (SELECT room_id FROM rooms WHERE room_number = 201);


\echo
\echo '=== Правило 2. Один клієнт не може жити в двох місцях одночасно ==='
\echo '2а. Коваленко вже проживає в номері 202, друге поточне проживання відхиляється'
INSERT INTO stays (client_id, room_id, checkin_date)
SELECT c.client_id, r.room_id, CURRENT_DATE
FROM clients c, rooms r
WHERE c.passport_number = 'ЕК123456' AND r.room_number = 102;

\echo '2б. Минулий період, що перетинається з її проживанням 2026-08-01..08-05, відхиляється'
INSERT INTO stays (client_id, room_id, checkin_date, checkout_date)
SELECT c.client_id, r.room_id, DATE '2026-08-03', DATE '2026-08-04'
FROM clients c, rooms r
WHERE c.passport_number = 'ЕК123456' AND r.room_number = 102;

\echo '2в. Минулий період, що не перетинається, допускається'
INSERT INTO stays (client_id, room_id, checkin_date, checkout_date)
SELECT c.client_id, r.room_id, DATE '2026-07-01', DATE '2026-07-05'
FROM clients c, rooms r
WHERE c.passport_number = 'ЕК123456' AND r.room_number = 102;

\echo 'Тестовий запис прибираємо:'
DELETE FROM stays
WHERE client_id = (SELECT client_id FROM clients WHERE passport_number = 'ЕК123456')
  AND room_id   = (SELECT room_id FROM rooms WHERE room_number = 102)
  AND checkin_date = DATE '2026-07-01';


\echo
\echo '=== Правило 3. У графіку прибирання можуть бути лише існуючі поверхи ==='
\echo '3а. Поверху 9 у готелі немає:'
INSERT INTO cleaning_schedule (employee_id, weekday, floor) VALUES (1, 2, 9);

\echo '3б. Перенести наявний графік на поверх 9 теж не можна:'
UPDATE cleaning_schedule SET floor = 9 WHERE employee_id = 1 AND weekday = 1;

\echo '3в. Додаємо номер 401 (новий поверх 4) і вносимо поверх 4 у графік:'
INSERT INTO rooms (room_number, floor, phone, room_type_id) VALUES (401, 4, '+380441234599', 1);
INSERT INTO cleaning_schedule (employee_id, weekday, floor) VALUES (1, 5, 4);

\echo '3г. Номер 401 останній на поверсі 4, який є в графіку: видалити його не можна:'
DELETE FROM rooms WHERE room_number = 401;

\echo 'Прибираємо тестові записи:'
DELETE FROM cleaning_schedule WHERE employee_id = 1 AND weekday = 5;
DELETE FROM rooms WHERE room_number = 401;


\echo
\echo '=== Підсумок: відхилені зміни не потрапили ні в базу, ні в кеш ==='
SELECT 'кеш' AS джерело, memcache_get('/availability') AS availability
UNION ALL
SELECT 'база', availability_json();
