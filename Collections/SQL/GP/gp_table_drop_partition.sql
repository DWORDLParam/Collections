-- Удаляем партиции по условию
-- DROP FUNCTION schema.gp_table_drop_partition(text, date, date);

CREATE OR REPLACE FUNCTION schema.gp_table_drop_partition(p_table_name text, p_beg_date date, p_end_date date)
	RETURNS TABLE (v_date date, v_sql text)
	LANGUAGE plpgsql
	VOLATILE
AS $$
DECLARE
x record;
v_beg_date date;
v_end_date date;
v_date date;
v_table_name text;
v_sql text;
BEGIN
	v_table_name = p_table_name;
	v_beg_date = p_beg_date;	
	v_end_date = p_end_date; 
	v_date = v_beg_date;
	create temp table temp_result (v_date date, v_sql text) ON COMMIT DROP;
	while v_date <= v_end_date loop 
		v_sql = 'ALTER TABLE '||v_table_name || ' DROP PARTITION IF EXISTS FOR ('''||v_date||''')';
        execute v_sql;
		insert into temp_result values (v_date,v_sql);
		v_date = v_date + interval '1' day;
	end loop;
	return query 
		select * from temp_result values;
END;
$$
EXECUTE ON ANY;