-- удаляет записи в таблице если она существует
drop function truncate_if_exists;
create or replace function truncate_if_exists(schema_name text, table_name text)
returns bool 
language plpgsql as $$
declare 
	f_result bool default false;
begin
    perform 1
    from information_schema.tables ist
    where ist.table_name = $2
    and ist.table_schema = $1;
    if found then
        execute format('truncate %s.%s', $1, $2);
        f_result := true;
    end if;
   return f_result;
end $$;


-- возвращает количество строк в таблице если она существует
drop function count_rows_if_exists;
create or replace function count_rows_if_exists(schema_name text, table_name text)
returns int 
language plpgsql as $$
declare 
	f_result int default -1;
begin
    perform 1
    from information_schema.tables ist
    where ist.table_name = $2
    and ist.table_schema = $1;
    if found then
        execute format('select count(*) from %s.%s', $1, $2) into f_result;
    end if;
   return f_result;
end $$;
