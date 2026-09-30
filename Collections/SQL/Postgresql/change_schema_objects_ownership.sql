
DROP FUNCTION schema.change_schema_objects_ownership(text, text);

CREATE OR REPLACE FUNCTION schema.change_schema_objects_ownership(p_schema text, p_role text)
	RETURNS void
	LANGUAGE plpgsql
	VOLATILE
AS $$
	 	
/*
--Функция изменяет владельца таблиц, представлений и функций в рамках схемы на указанную роль
*/

declare
  v_object record;
  v_view record;
  v_funct_indentity_args text;
  v_test text;
  v_suffix text;
begin

  raise notice '-------------------------------------------------';
  raise notice 'Function started at %', localtimestamp;
  raise notice 'Working in schema % ', p_schema;

  -- Tables
  raise notice 'Checking tables...';

  for v_object in
          select distinct c.relname, a.rolname,c.relkind, pl.mode
          from pg_class c
          left join pg_namespace n ON c.relnamespace = n.oid
          left join pg_authid a ON c.relowner = a.oid
		  left join pg_locks pl on c.oid=pl.relation
          where n.nspname = p_schema and c.relkind in ('r')
  loop
                if v_object.rolname = p_role then
                    continue;
				elsif v_object.mode IS NOT NULL then
				    raise notice 'Table %.% is locked, skipping...',p_schema, v_object.relname;
					continue;
                else
                  raise notice 'Current owner of %.% is %', p_schema, v_object.relname, v_object.rolname;
                  raise notice 'Changing owner of %.% to %', p_schema, v_object.relname, p_role;
                  execute 'alter table '||p_schema||'.'||v_object.relname||' owner to '||p_role||';';
                  raise notice 'Granting SELECT on %.% to %', p_schema, v_object.relname, p_role;
                  execute 'grant select on table '||p_schema||'.'||v_object.relname||' to '||p_role||';';

                end if;
  end loop;


  -- Views 
  raise notice 'Checking views...';
 
  for v_view in
    select viewname,viewowner
	from pg_catalog.pg_views pv
	where pv.schemaname = p_schema
  loop
    if v_view.viewowner = p_role then
      continue;  
	else
	  raise notice 'Current owner of %.% is %', p_schema, v_view.viewname, v_view.viewowner;
      raise notice 'Changing owner of %.% to %', p_schema, v_view.viewname, p_role;
      execute 'alter table '||p_schema||'.'||v_view.viewname||' owner to '||p_role||';';
    end if;	
  end loop;
  
  for v_view in
                SELECT v.table_schema,
                           v.table_name
                FROM information_schema.views v
                LEFT JOIN
                  (SELECT TABLE_NAME,
                                  table_schema
                   FROM information_schema.role_table_grants
                   WHERE table_schema=p_schema
                   AND privilege_type='SELECT' ) r ON v.table_schema=r.table_schema
                   AND v.table_name=r.table_name
                WHERE v.table_schema=p_schema
                AND r.table_name IS NULL

  loop
    raise notice 'Granting SELECT on %.% to %', p_schema, v_view.table_name, p_role;
    execute 'grant select on table '||p_schema||'.'||v_view.table_name||' to '||p_role||';';
  end loop;

   --
   -- Functions
 raise notice 'Checking functions...';

   for v_object in
   select p.oid, p.proname, a.rolname
   from pg_proc p
   left join pg_namespace nsp ON p.pronamespace = nsp.oid
   left join pg_authid a ON p.proowner = a.oid
   where nsp.nspname = p_schema
   loop
     if v_object.rolname = p_role then
            continue;
         else
           v_funct_indentity_args := pg_get_function_identity_arguments(v_object.oid);

           raise notice 'Current owner of function %.%( % ) is %', p_schema, v_object.proname, v_funct_indentity_args, v_object.rolname;
           raise notice 'Changing owner of function %.%( % ) to %', p_schema, v_object.proname, v_funct_indentity_args, p_role;
           execute 'alter function '||p_schema||'.'||v_object.proname||'('||v_funct_indentity_args||') owner to '||p_role||';';
           raise notice 'Granting EXECUTE on %.%( % ) to %', p_schema, v_object.proname, v_funct_indentity_args, p_role;
	       execute 'grant execute on function '||p_schema||'.'||v_object.proname||'('||v_funct_indentity_args||') to '||p_role||';';

        end if;
  end loop;

  raise notice 'Function Finished at %', localtimestamp;
  raise notice '----------------------------------------------';

end;
 
$$;
