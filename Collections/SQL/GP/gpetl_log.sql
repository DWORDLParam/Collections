-- пишем лог 

-- DROP FUNCTION logs.gpetl_log(text, text, text, int8, int4);

CREATE OR REPLACE FUNCTION logs.gpetl_log(p_event_type text, p_event_message text, p_location text DEFAULT NULL::text, p_part_id int8 DEFAULT NULL::bigint, p_exec_id int4 DEFAULT NULL::integer)
	RETURNS void
	LANGUAGE plpgsql
	VOLATILE
AS $$

declare
    v_event_type    text;
    v_debug         boolean := true;
    v_notice        boolean := true;
    v_log_debug     boolean := false;
    v_event_message text;
    v_sqlexpression text;
begin
    --Check message type
    v_event_type = upper(p_event_type);
    if v_event_type not in ('ERROR', 'INFO', 'WARN', 'DEBUG') then
        raise exception 'Illegal event type! Use one of: INFO, WARN, ERROR, DEBUG';
    end if;

    if v_event_type = 'DEBUG' and v_debug = false then
        return;
    end if;

    if v_notice then
        raise notice '%: <%> Location[%] Order[%] Exec[%]', v_event_type, p_event_message, p_location, p_part_id, p_exec_id;
    end if;

    if v_event_type = 'DEBUG' and v_log_debug = false then
        return;
    end if;

    v_event_message := replace(p_event_message, '''', '''''');

    v_sqlexpression := 'INSERT INTO logs.audit(auditId, partId, eventType, eventMsg, eventLocation, isError, execid)
                    VALUES ( ' || nextval('logs.audit_seq') || ' , ' ||
                       coalesce(to_char(p_part_id, '999999999999'), 'null') || ', ''' || v_event_type || ''', ' ||
                       coalesce('''' || v_event_message || '''', '''null''') || ', ' ||
                       coalesce('''' || p_location || '''', 'null') || ', ' ||
                       case when v_event_type = 'ERROR' THEN true else false end || ', ' ||
                       coalesce(to_char(p_exec_id, '999999999999'), 'null') || ');';

    perform dblink_exec(format('dbname=%s host=%s port=%s user=%s password=%s',
                               current_database()::text,
                               (select address::text
                                from pg_catalog.gp_segment_configuration
                                where content = -1
                                  and "role" = 'p'),
                               '5432'::text,
                               'logmaster'::text,
                               'xxxxxxxxxxxx'::text),
                        v_sqlexpression);
end

$$
EXECUTE ON ANY;