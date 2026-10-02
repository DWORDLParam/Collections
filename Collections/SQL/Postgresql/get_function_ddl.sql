-- получаем текст функции по наименованию
-- DROP FUNCTION schema.get_function_ddl(text);

CREATE OR REPLACE FUNCTION schema.get_function_ddl(p_function text)
	RETURNS _text
	LANGUAGE plpgsql
	VOLATILE
AS $$
	
declare
    v_schema   text[] :=
        case position('.' in p_function)
            when 0 then (select array_agg(n.nspname)
                         from pg_proc p,
                              pg_namespace n
                         where p.pronamespace = n.oid
                           and p.proname = p_function)
            else array [split_part(p_function, '.', 1)] end;
    v_function text   := case position('.' in p_function) when 0 then p_function else split_part(p_function, '.', 2) end;
begin
    return (select array_agg(schema.get_function_ddl(p.oid))
            from pg_proc p,
                 pg_namespace n
            where p.pronamespace = n.oid
              and p.proname = v_function
              and n.nspname = any (v_schema));
end

$$;


-- получаем текст функции по oid
-- DROP FUNCTION schema.get_function_ddl(oid);

CREATE OR REPLACE FUNCTION schema.get_function_ddl(p_function_oid oid)
	RETURNS text
	LANGUAGE sql
	VOLATILE
	STRICT
AS $$
	
with proc as (select p.oid                                                                  proc_id,
                     quote_ident(n.nspname) || '.' || quote_ident(p.proname)                function,
                     case
                         when p.proretset then chr(10) || chr(9) || 'cost ' || procost::text
                         else '' end                                                        cost_str,
                     case when p.proiswindow then chr(10) || chr(9) || 'window' else '' end window_str,
                     coalesce(chr(10) || chr(9) || case p.provolatile
                                                       when 'i' then 'immutable'
                                                       when 's' then 'stable'
                                                       when 'v' then 'volatile' end, '')    volatile_str,
                     coalesce(chr(10) || chr(9) || case p.prodataaccess
                                                       when 'n' then 'no sql'
                                                       when 'c' then 'contains sql'
                                                       when 'm' then 'modifies sql data'
                                                       when 'r' then 'reads sql data' end,
                              '')                                                           dataaccess_str,
                     case when p.proisstrict then chr(10) || chr(9) || 'strict' else '' end strict_str,
                     case
                         when p.prosecdef then chr(10) || chr(9) || 'security definer'
                         else '' end                                                        security_str,
                     coalesce(chr(10) || chr(9) || 'execute on ' || case p.proexeclocation
                                                                        when 'm' then 'master'
                                                                        when 'i' then 'initplan'
                                                                        when 'a' then 'any'
                                                                        when 's' then 'all segments' end,
                              '')                                                           execlocation_str,
                     p.prosrc,
                     p.prolang,
                     p.proowner,
                     p.proacl,
                     case
                         when exists(select 1
                                     from aclexplode(p.proacl) g
                                     where g.grantee = 0) or p.proacl is null
                             then ''
                         else chr(10) || 'revoke execute on function ' || p.oid::regprocedure::text ||
                              ' from public;' end                                           revoke_str,
                     coalesce(chr(10) || 'comment on function ' || p.oid::regprocedure::text || ' is ' ||
                quote_literal(obj_description(p.oid)) || ';', '') comment_str,
                    'alter function ' || p.oid::regprocedure::text || ' owner to ' || (pg_get_userbyid(p.proowner)) || ';' owner_str
              from pg_proc p,
                   pg_namespace n
              where p.pronamespace = n.oid
                and p.oid = p_function_oid)
select 'create or replace function ' || p.function || '(' ||
       pg_get_function_arguments(p.proc_id) || ')' ||
       chr(10) || chr(9) || 'returns ' || pg_get_function_result(p.proc_id) ||
       chr(10) || chr(9) || 'language ' || l.lanname ||
       p.window_str ||
       p.volatile_str ||
       p.strict_str ||
       p.dataaccess_str ||
       p.security_str ||
       p.execlocation_str ||
       p.cost_str ||
       chr(10) || 'as' || chr(10) || chr(36) || chr(36) || p.prosrc || chr(36) || chr(36) || ';' || chr(10) ||
       p.owner_str ||
       coalesce(pr.grant_script, '') ||
       p.revoke_str ||
       p.comment_str
from proc p
         left join (select proc_id,
                           string_agg(chr(10) || grant_script, '') grant_script
                    from (select proc_id,
                                 'grant ' || privilege_type || ' on function ' ||
                                 proc_id::regprocedure::text ||
                                 ' to ' || string_agg(grantee, ', ') ||
                                 case when is_grantable then ' with grant option' else '' end ||
                                 ';' grant_script
                          from (select proc_id,
                                       case grantee when 0 then 'public' else quote_ident(pg_get_userbyid(grantee)) end grantee,
                                       is_grantable,
                                       string_agg(privilege_type, ', ')                                    privilege_type
                                from (select proc_id,
                                             (aclexplode(proacl)).grantee,
                                             (aclexplode(proacl)).grantor,
                                             (aclexplode(proacl)).privilege_type,
                                             (aclexplode(proacl)).is_grantable
                                      from proc) p
                                where grantee <> grantor
                                group by 1, 2, 3) pr
                          group by proc_id, privilege_type, is_grantable) pr
                    group by 1) pr on p.proc_id = pr.proc_id,
     pg_language l
where p.prolang = l.oid

$$;

