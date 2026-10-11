-- Получаем исходный код счетчика

-- DROP FUNCTION schema.gp_get_sequence_ddl(text);

CREATE OR REPLACE FUNCTION schema.gp_get_sequence_ddl(p_sequence text)
	RETURNS text
	LANGUAGE plpgsql
	VOLATILE
AS $$
	
declare
    v_result text;
begin
    execute format('
select ''create'' || case c.relpersistence when ''t'' then '' temp'' else '''' end || '' sequence '' || c.oid::regclass::text ||
       chr(10) || chr(9) || ''increment '' || s.increment_by::text ||
       chr(10) || chr(9) || ''minvalue '' || s.min_value::text ||
       chr(10) || chr(9) || ''maxvalue '' || s.max_value::text ||
       chr(10) || chr(9) || ''start '' || s.start_value::text ||
       chr(10) || chr(9) || ''cache '' || s.cache_value::text ||
       chr(10) || chr(9) || case s.is_cycled when false then ''no '' else '''' end || ''cycle'' ||
       coalesce(chr(10) || chr(9) || ''owned by '' || d.refobjid::regclass::text || ''.'' || quote_ident(a.attname), '''') ||
       '';'' ||
       chr(10) || ''alter sequence '' || c.oid::regclass::text || '' owner to '' ||
       quote_ident(pg_get_userbyid(c.relowner)) || '';'' ||
       coalesce((select string_agg(chr(10) || grant_script, '''') grant_script
                 from (select ''grant '' || privilege_type || '' on sequence '' || c.oid::regclass::text ||
                              '' to '' ||
                              string_agg(grantee, '', '' order by 1) || case is_grantable
                                                               when true
                                                                   then '' with grant option''
                                                               else '''' end ||
                              '';'' grant_script
                       from (select case grantee when 0 then ''public'' else pg_get_userbyid(grantee) end grantee,
                                    is_grantable,
                                    string_agg(privilege_type, '', '' order by 1) privilege_type
                             from (select (aclexplode(c.relacl)).grantor,
                                          (aclexplode(c.relacl)).grantee,
                                          (aclexplode(c.relacl)).privilege_type,
                                          (aclexplode(c.relacl)).is_grantable) a
                             where grantor <> grantee
                             group by 1, 2) a
                       group by privilege_type, is_grantable) a), '''') ||
       coalesce(chr(10) || ''comment on sequence '' || c.oid::regclass::text || '' is '' ||
                quote_literal(obj_description(c.oid)) || '';'', '''')
from %s s,
     pg_class c
         left join pg_depend d on c.oid = d.objid and d.deptype = ''a''
         left join pg_attribute a on a.attrelid = d.refobjid and a.attnum = d.refobjsubid
where c.relkind = ''S''
  and c.oid = %s', p_sequence, p_sequence::regclass::oid::text) into v_result;
    return v_result;
end

$$
EXECUTE ON ANY;


---------------------------

-- DROP FUNCTION schema.gp_get_sequence_ddl(oid);

CREATE OR REPLACE FUNCTION schema.gp_get_sequence_ddl(p_sequence_oid oid)
	RETURNS text
	LANGUAGE plpgsql
	VOLATILE
	STRICT
AS $$
	
declare
    v_result text;
begin
    execute format('
select ''create'' || case c.relpersistence when ''t'' then '' temp'' else '''' end || '' sequence '' || c.oid::regclass::text ||
       chr(10) || chr(9) || ''increment '' || s.increment_by::text ||
       chr(10) || chr(9) || ''minvalue '' || s.min_value::text ||
       chr(10) || chr(9) || ''maxvalue '' || s.max_value::text ||
       chr(10) || chr(9) || ''start '' || s.start_value::text ||
       chr(10) || chr(9) || ''cache '' || s.cache_value::text ||
       chr(10) || chr(9) || case s.is_cycled when false then ''no '' else '''' end || ''cycle'' ||
       coalesce(chr(10) || chr(9) || ''owned by '' || d.refobjid::regclass::text || ''.'' || quote_ident(a.attname), '''') ||
       '';'' ||
       chr(10) || ''alter sequence '' || c.oid::regclass::text || '' owner to '' ||
       quote_ident(pg_get_userbyid(c.relowner)) || '';'' ||
       coalesce((select string_agg(chr(10) || grant_script, '''') grant_script
                 from (select ''grant '' || privilege_type || '' on sequence '' || c.oid::regclass::text ||
                              '' to '' ||
                              string_agg(grantee, '', '' order by 1) || case is_grantable
                                                               when true
                                                                   then '' with grant option''
                                                               else '''' end ||
                              '';'' grant_script
                       from (select case grantee when 0 then ''public'' else quote_ident(pg_get_userbyid(grantee)) end grantee,
                                    is_grantable,
                                    string_agg(privilege_type, '', '' order by 1) privilege_type
                             from (select (aclexplode(c.relacl)).grantor,
                                          (aclexplode(c.relacl)).grantee,
                                          (aclexplode(c.relacl)).privilege_type,
                                          (aclexplode(c.relacl)).is_grantable) a
                             where grantor <> grantee
                             group by 1, 2) a
                       group by privilege_type, is_grantable) a), '''') ||
       coalesce(chr(10) || ''comment on sequence '' || c.oid::regclass::text || '' is '' ||
                quote_literal(obj_description(c.oid)) || '';'', '''')
from %s s,
     pg_class c
         left join pg_depend d on c.oid = d.objid and d.deptype = ''a''
         left join pg_attribute a on a.attrelid = d.refobjid and a.attnum = d.refobjsubid
where c.relkind = ''S''
  and c.oid = %s', p_sequence_oid::regclass::text, p_sequence_oid::text) into v_result;
    return v_result;
end

$$
EXECUTE ON ANY;