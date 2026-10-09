-- Процедура копирует записи одной таблицы в другую с помощью курсора (избегаем блокировок в источнике)

create or replace function schema.format_value_type(in_value anyelement, vt char)
returns varchar 
language plpgsql
as 
$$
declare 
	result varchar;
	s1 varchar;
begin
case vt
when 'c' then
	s1 = replace(in_value::text,'"','');
	result := format('%L',s1); 
when 'd','t' then 
	result := format('%L',in_value); 
when 'b' then
	if in_value::text = 't' then
	result := true;
	else result := false;
	end if;
else result :=  in_value;
end case;	
return result;
end;	
$$;

-- drop procedure schema.copy_records_by_cursor;
create or replace procedure schema.copy_records_by_cursor(
	from_table varchar,
	to_table varchar,
	fields varchar[],
	filter_expression varchar default '')
language plpgsql
as
$$
declare
	fields_str varchar;
	values_str varchar;
	cur refcursor;
	cur_record RECORD;
	a1 text[];
	a2 varchar[];
	r_counter int := 0;
begin

	for i in 1..array_length(fields, 1) loop
	fields_str = concat_ws(',',fields_str,fields[i][1]);	
	end loop;

	if filter_expression = '' then
	filter_expression = '1=1'; 
	end if;
	
	execute format('truncate table %s',to_table);	
	open cur for execute format('SELECT %s FROM %s WHERE %s',fields_str, from_table, filter_expression);

	loop
	fetch next from cur into cur_record;
	exit when not found;

	r_counter = r_counter+1; 
	a1 = string_to_array(replace(replace(cur_record::text,'(',''),')',''),',','');
	a2 = ARRAY[]::varchar[];

	for i in 1..array_length(fields, 1) loop
	a2 = array_append(a2, public.format_value_type(a1[i],fields[i][2]));
	end loop;
	values_str = array_to_string(a2, ',', '*');

	execute format('insert into %s (%s) values (%s)',to_table, fields_str, values_str);
	if (r_counter % 100000) = 0 then
	raise notice '% -> % records copied', clock_timestamp()::time, r_counter;	
	end if;

	end loop;
	raise notice '% -> % total records copied', clock_timestamp()::time, r_counter;	
	close cur;	
end;
$$;