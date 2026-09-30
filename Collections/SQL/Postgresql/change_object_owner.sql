DROP FUNCTION schema.change_object_owner(oid, name, name, name, text, text, text);

CREATE OR REPLACE FUNCTION schema.change_object_owner(p_oid oid, p_schema_name name, p_object_name name, p_owner_name name, p_object_type text, p_type_of_script text, p_sql text)
	RETURNS bool
	LANGUAGE plpgsql
	VOLATILE
AS $$
	
declare
    v_error_message text    := null;
    v_result        boolean := true;
begin
    if not exists(select 1 from pg_locks where relation = p_oid) then
        begin
            execute p_sql;
        exception
            when insufficient_privilege then
                v_error_message := 'insufficient_privilege';
            when undefined_table then
                v_error_message := 'undefined_table';
            when undefined_object then
                v_error_message := 'role does not exist';
            when others then
                v_error_message := 'Other_error';
        end;
    else
        v_error_message := 'Table is locked';
    end if;
    if v_error_message is null then
        insert into schema.scripts_hist (datetime_exec, table_oid, schema_name, object_name,
                                                                   owner_name, obj_type, type_of_script_change_rules,
                                                                   script_change_rules)
        values (current_timestamp, p_oid, p_schema_name, p_object_name, p_owner_name, p_object_type, p_type_of_script,
                p_sql);
    else
        insert into schema.privelege_errors (datetime_exec, table_oid, schema_name, object_name,
                                                             owner_name, obj_type, type_of_script_change_rules,
                                                             script_change_rules, error_time, error_message,
                                                             error_comment)
        values (current_timestamp, p_oid, p_schema_name, p_object_name, p_owner_name, p_object_type, p_type_of_script,
                p_sql, current_timestamp, v_error_message, '');
        v_result := false;
    end if;
    return v_result;
end

$$;
