-- Завершает процесс по PID
-- DROP FUNCTION myschema.cancel_backend(int4, text);

CREATE OR REPLACE FUNCTION myschema.cancel_backend(p_pid int4, p_message text)
	RETURNS text
	LANGUAGE plpgsql
	VOLATILE
AS $$
	
declare
    v_message       text;
    v_usename       text;
    v_query         text;
    v_action_result boolean;
begin
    select usename, query
    into v_usename, v_query
    from get_pg_stat_activity()
    where pid = p_pid;

    select mdb_toolkit.gp_cancel_backend(p_pid)
    into v_action_result;

    select case
               when v_action_result
                   then format('{"who_did_it":"%s","user_name":"%s","query":"%s", "comment":"%s"}',
                               current_user,
                               v_usename,
                               replace(
                                       replace(
                                               replace(
                                                       replace(
                                                               replace(v_query, '\', '\\'),
                                                               chr(10), '\n'),
                                                       '"', '\"'),
                                               chr(13), ''),
                                       chr(9), '\t'),
                               p_message)
               else 'Не удалось отменить процесс ' || p_pid::text end
    into v_message;

    perform logs.gpetl_log(case when v_action_result then 'INFO' else 'ERROR' end, v_message, 'service.cancel_backend',
                           null, null);
    return v_message;
end

$$
EXECUTE ON ANY;

