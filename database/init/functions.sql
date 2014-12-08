---
--- Convert Fahrenheit to Celsuis
---
CREATE OR REPLACE FUNCTION f2c(real) RETURNS double precision
	LANGUAGE sql AS $_$
		SELECT ($1 - 32.0) / 1.8
	$_$;
COMMENT on FUNCTION f2c(real) IS 'Convert F to C f2c(temperature)';

---
--- Compute wind chill
---
CREATE OR REPLACE FUNCTION wcht(real, real) RETURNS double precision
	LANGUAGE sql AS $_$
		SELECT case when ($1 is null or $2 is null) THEN null ELSE
			(case when $2 < 1 or $1 > 32 THEN $1 ELSE
				35.74 + .6215 * $1 - 35.75 * power($2 * 1.15,0.16) 
						+ .4275 * $1 * power($2 * 1.15,0.16)
			END)
		END 
	$_$;
COMMENT on FUNCTION wcht(real, real) IS 'Wind Chill wcht(tmpf, sknt)';

CREATE OR REPLACE FUNCTION hdd65(real, real) RETURNS numeric
 	LANGUAGE sql
 	AS $_$select (case when (65 - (( $1 + $2 )/2.)) > 0 then (65. - ( $1 + $2 )/2.) else 0 end)::numeric$_$;

---
--- Unsure of current usage of this, legacy asos database stuff perhaps
---
CREATE FUNCTION wind_chill(real, real) RETURNS double precision
    LANGUAGE sql
    AS $_$select 35.74 + .6215 * $1 - 35.75 * power($2 * 1.15,0.16) + .4275 * $1 * power($2 * 1.15,0.16)$_$;
 	