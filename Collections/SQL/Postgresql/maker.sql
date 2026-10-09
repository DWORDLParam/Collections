-- создаем схемы на основе списка в подключаемой таблице
create or replace procedure SchemaMaker()
language plpgsql
as $$
declare 
 rec record;
 conn bool;	
begin 
	
	
conn := (SELECT dblink_connect('host=1.1.1.1 user=admin password=password dbname=db') = 'OK');

if conn then

	for rec in (
		SELECT * FROM dblink('host=1.1.1.1 user=admin password=password dbname=db',
    	'SELECT distinct table_schema FROM import.columns_v2'
		) AS remote_t(table_schema varchar)
	)
	loop 
		EXECUTE 'drop schema if exists ' ||  rec.table_schema || ' ';
		EXECUTE 'create schema ' ||  rec.table_schema || ' ';
		raise notice 'schema % created', rec.table_schema;	
	end loop;

end if;

PERFORM dblink_disconnect();
end;
$$;




-- создаем последовательности на основе списка в подключаемой таблице
create or replace procedure SequenceMaker(
				host_string varchar,
				user_name varchar,
				password_string varchar,
				db_name varchar)
language plpgsql
as $$
declare
	connection_string varchar;
	connected bool;
	rec_seq record;
	sql_expression varchar;
	msg_text text;
begin
	
connection_string := format('host=%s user=%s password=%s dbname=%s', host_string, user_name, password_string, db_name); 
connected := (SELECT dblink_connect(connection_string) = 'OK');
if connected then

	create temporary table table_data on commit drop as 
	select * FROM dblink(connection_string, 'SELECT table_schema, column_default from import.columns_v2') AS remote_t(table_schema varchar, column_default varchar);

	for rec_seq in (select  
					table_schema,
					trim(both '''' from replace(replace(column_default, 'nextval(', ''),'::regclass)','')) as seq_name
					from table_data 
					where column_default like '%nextval%')
	loop
	sql_expression := format('drop sequence if exists %s ;',rec_seq.seq_name);	
	sql_expression := sql_expression || format(' create sequence  %s INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 START 1 CACHE 1 NO CYCLE;',rec_seq.seq_name);

		begin
			
		EXECUTE sql_expression;

		exception when others then
		get STACKED DIAGNOSTICS
		msg_text = MESSAGE_TEXT;

   		raise notice 'ERROR MESSAGE TEXT: %', msg_text;
  		end;
  	
	raise notice 'Sequence % created', rec_seq.seq_name;	
	end loop;

end if;
end;
$$;





-- создаем таблицы
drop procedure TableMaker;
create or replace procedure TableMaker(
				host_string varchar,
				user_name varchar,
				password_string varchar,
				db_name varchar)
language plpgsql
as $$
declare 
	rec_schema record;
	rec_table record;
	rec_column record;
	connection_string varchar;
	connected bool;
	r_count int;
	sql_expression varchar;
	n_precision varchar;
	n_scale varchar;
	f_size varchar;
	f_result_size varchar;
	v_default varchar;
	v_nullable varchar;
	v_data_type varchar;
	msg_text text;
begin 
	
connection_string := format('host=%s user=%s password=%s dbname=%s', host_string, user_name, password_string, db_name); 
connected := (SELECT dblink_connect(connection_string) = 'OK');
if connected then

	create temporary table table_data on commit drop as 
	select * FROM dblink(connection_string, 
	'SELECT table_schema, table_name, column_name, ordinal_position, column_default, is_nullable, character_maximum_length, numeric_precision, numeric_scale, udt_name FROM import.columns_v2') AS remote_t(
	table_schema varchar,
	table_name varchar,
	column_name varchar,
	ordinal_position int4,
	column_default varchar,
	is_nullable varchar,
	character_maximum_length int8,
	numeric_precision int8,
	numeric_scale int8,
	udt_name varchar
	);
	r_count := (select count(*) from table_data);
	raise notice 'temporary table created (row count %)', r_count;		

	<<loop1>>
	for rec_schema in (select distinct table_schema from table_data order by 1)
	loop

		for rec_table in (select distinct table_name from table_data where table_schema = rec_schema.table_schema)
		loop
			
			sql_expression := format('CREATE TABLE %s.%s (',rec_schema.table_schema,rec_table.table_name);
		
			for rec_column in (
			select 
			column_name,
			column_default,
			is_nullable,
			character_maximum_length,
			numeric_precision,
			numeric_scale,
			udt_name
			from table_data where table_schema = rec_schema.table_schema and table_name = rec_table.table_name order by ordinal_position
			)
			loop 
			
			-- размер символьного поля		
			if rec_column.character_maximum_length is not null then f_size := '(' || rec_column.character_maximum_length::text || ')';
			else f_size := '';
			end if;	
			-- количество знаков после запятой 
			if rec_column.numeric_scale is not null then n_scale := rec_column.numeric_scale::text;
			else n_scale := '0';
			end if;
			-- количество разрядов в числе с плавающей точкой 
			if rec_column.numeric_precision is not null then n_precision := '(' || rec_column.numeric_precision::text || ',' || n_scale || ')';
			else n_precision := '';
			end if;
			
			-- указываем размерность поля 
			case rec_column.udt_name
			when 'varchar' then f_result_size := f_size;
			when 'numeric' then f_result_size := n_precision;
			else f_result_size := '';
			end case;		
		
			-- значение по умолчанию
			if rec_column.column_default is not null then v_default := ' DEFAULT ' || rec_column.column_default;
			else v_default := '';
			end if;
		
			-- Обязательное значение
			if rec_column.is_nullable = 'YES' then v_nullable := ' NULL,';
			else v_nullable := ' NOT NULL,';
			end if;			
		
			-- Кооректировка типа данных
			if rec_column.udt_name = 'unknown' then v_data_type := 'text';
			else v_data_type := rec_column.udt_name;
			end if;
		
			sql_expression := sql_expression || '"' || rec_column.column_name || '" ' || v_data_type || f_result_size || v_default || v_nullable;
			
			end loop;
			
			--sql_expression := SUBSTRING(sql_expression FROM 1 FOR LENGTH(sql_expression)-1) || ');';
			sql_expression := TRIM(TRAILING ',' FROM sql_expression) || ');';
			
			begin
			
			EXECUTE sql_expression;
	
			exception when others then
			get STACKED DIAGNOSTICS
			msg_text = MESSAGE_TEXT;

   			raise notice 'ERROR MESSAGE TEXT: %', msg_text;
   			raise notice 'Expression: %', sql_expression;
   			exit loop1;
  			end;
		
		raise notice 'table % created', rec_table.table_name;	
		end loop;
	end loop loop1;

PERFORM dblink_disconnect();
end if;
end;
$$;





-- очищаем схемы от таблиц
create or replace procedure TableCleaner(
				host_string varchar,
				user_name varchar,
				password_string varchar,
				db_name varchar)
language plpgsql
as $$
declare 
	rec_schema record;
	rec_table record;
	connection_string varchar;
	connected bool;
	sql_expression varchar;
	msg_text text;
begin 
	
connection_string := format('host=%s user=%s password=%s dbname=%s', host_string, user_name, password_string, db_name); 
connected := (SELECT dblink_connect(connection_string) = 'OK');
if connected then

	create temporary table table_data on commit drop as 
	select * FROM dblink(connection_string, 
	'SELECT table_schema, table_name FROM import.columns_v2') AS remote_t(
	table_schema varchar,
	table_name varchar
	);

	for rec_schema in (select distinct table_schema from table_data order by 1)
	loop
		for rec_table in (select distinct table_name from table_data where table_schema = rec_schema.table_schema)
		loop
			sql_expression := format('drop table if exists %s.%s ;',rec_schema.table_schema,rec_table.table_name);
		
			begin
			
			EXECUTE sql_expression;
	
			exception when others then
			get STACKED DIAGNOSTICS
			msg_text = MESSAGE_TEXT;

   			raise notice 'ERROR MESSAGE TEXT: %', msg_text;
   			raise notice 'Expression: %', sql_expression;
  			end;
		
			raise notice 'table % droped', rec_table.table_name;
		end loop;	
	end loop;
	

PERFORM dblink_disconnect();
end if;
end;
$$;