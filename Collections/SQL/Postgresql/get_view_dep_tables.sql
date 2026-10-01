-- возвращает список таблиц используемых в представлении
-- DROP FUNCTION schema.get_view_dep_tables(text);

CREATE OR REPLACE FUNCTION schema.get_view_dep_tables(view_name text)
 RETURNS TABLE(table_name text)
 LANGUAGE plpgsql
AS $$
	
    begin
        return query
        SELECT distinct d.refobjid::regclass::text
        FROM pg_depend AS d -- зависимые объекты
                 JOIN pg_rewrite AS r
                      ON r.oid = d.objid
                 JOIN pg_class AS v
                      ON v.oid = r.ev_class
        WHERE v.relkind = 'v' -- только представления
          AND v.oid = (view_name)::regclass
          AND d.refobjid <> v.oid
          AND d.classid = 'pg_rewrite'::regclass
          AND d.deptype = 'n' -- нормальная зависимость
          AND d.refclassid = 'pg_class'::regclass 
        ;
    exception
        when others then
            RAISE NOTICE 'ERROR CODE: %. MESSAGE TEXT: %, RELATION:%', SQLSTATE, SQLERRM,  view_name;
    end;

$$;