-- Получаем определение роли пользователя

-- DROP FUNCTION schema.gp_get_role_ddl(varchar);
CREATE OR REPLACE FUNCTION schema.gp_get_role_ddl(p_role varchar)
	RETURNS text
	LANGUAGE plpgsql
	VOLATILE
AS $$
	
begin
    return (
		WITH 
		roles_assigned AS
		(         SELECT gp_roles_assigned.ramemberid,
		            gp_roles_assigned.ramembername,
		            string_agg(gp_roles_assigned.rarolename,',') roles
		           FROM gp_toolkit.gp_roles_assigned
		          WHERE gp_roles_assigned.ramembername IS NOT NULL
		          GROUP BY 1,2
		)
		, protocol_assigned AS 
		(
			SELECT  role_id , rolname, string_agg(protocol_script,'') AS protocol_script
			FROM
			(
				SELECT  grantee AS role_id, rolname, 'GRANT ' || string_agg(DISTINCT privilege_type,',') || ' ON protocol ' || _protocol || ' to ' || rolname || ';' || CHR(10) AS protocol_script
				FROM
				(
					SELECT pe.ptcname AS _protocol, (aclexplode(ptcacl)).grantee, (aclexplode(ptcacl)).privilege_type
					FROM pg_catalog.pg_extprotocol pe
				) pe 
					JOIN pg_catalog.pg_roles pr ON pe.grantee=pr.oid
				GROUP BY grantee, rolname, _protocol	
			) pe
			GROUP BY role_id, rolname
		)
		SELECT 
			'CREATE ROLE '||pr.rolname||chr(10)||
			'with '|| 
		 	CASE WHEN rolcanlogin THEN 'LOGIN'||chr(10)||'PASSWORD ''temppass''' ELSE 'NOLOGIN' END 	||chr(10)||
		 	CASE WHEN rolsuper THEN 'SUPERUSER' ELSE 'NOSUPERUSER' END 	||chr(10)||
			CASE WHEN rolcreaterole THEN 'CREATEROLE ' ELSE  'NOCREATEROLE' END || chr(10)||
			CASE WHEN rolcreatedb THEN 'CREATEDB ' ELSE  'NOCREATEDB' END || chr(10)||
			CASE WHEN pr.rolcreaterextgpfd  THEN 'CREATEEXTTABLE (type=''readable'',protocol=''gpfdist'')'|| chr(10) ELSE  ''  END ||
			CASE WHEN pr.rolcreatewextgpfd  THEN 'CREATEEXTTABLE (type=''writable'',protocol=''gpfdist'')'|| chr(10) ELSE  ''  END ||
			CASE WHEN ra.roles IS null THEN '' ELSE  'IN ROLE ' || ra.roles || chr(10) END ||
			'CONNECTION LIMIT '|| rolconnlimit ||chr(10)||
			'RESOURCE GROUP '|| (SELECT pr.rsgname FROM pg_catalog.pg_resgroup pr WHERE oid=rolresgroup) 
			 ||';'|| 
			 CASE WHEN pa.protocol_script IS NULL THEN '' ELSE CHR(10) || pa.protocol_script end
		FROM pg_catalog.pg_roles pr
			LEFT JOIN roles_assigned ra ON pr.oid = ra.ramemberid
			LEFT JOIN protocol_assigned pa ON pa.role_id = pr.oid
		WHERE pr.rolname =p_role
    );
END

$$
EXECUTE ON ANY;