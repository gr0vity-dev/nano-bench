DROP TABLE IF EXISTS test_pregen ;
CREATE TABLE test_pregen (
    test_id         CHAR(64),
    node_name       CHAR(32),
    start_time      FLOAT,
    end_time        FLOAT,
    duration_s      FLOAT,
  	bps             FLOAT
);
CREATE INDEX idx_test_pregen_test_id_node_name ON test_pregen (test_id,node_name);
alter table test_pregen add column suite_id CHAR(64);


DROP TABLE IF EXISTS test_publish ;
CREATE TABLE test_publish (
    test_id         CHAR(64),
    node_name       CHAR(32),
    start_time      FLOAT,
    end_time        FLOAT,
    duration_s      FLOAT,
  	bps             FLOAT,
    is_sync         BOOLEAN
);
CREATE INDEX idx_test_publish_test_id_node_name ON test_publish (test_id,node_name);
alter table test_publish add column suite_id CHAR(64);


DROP TABLE IF EXISTS test_confirmations ;
CREATE TABLE test_confirmations (
    test_id                 CHAR(64),
    conf_count_expected     INT,
    start_date              CHAR(22),
    duration_first_conf     FLOAT,
    end_date                CHAR(22),
    duration_s              FLOAT,
    conf_10p                FLOAT,
    conf_25p                FLOAT,    
    conf_p50                FLOAT,
    conf_p75                FLOAT,
    conf_p90                FLOAT,
    conf_p99                FLOAT,
    conf_p100               FLOAT,    
    cps_p10                 FLOAT,
    cps_p25                 FLOAT,
    cps_p50                 FLOAT,
    cps_p75                 FLOAT,
    cps_p90                 FLOAT,
    cps_p99                 FLOAT,
    cps_p100                FLOAT,    
    node_is_publisher       BOOLEAN,
    node_name               CHAR(32),
    node_version            CHAR(20),
    conf_count_all          INT,
    conf_count_in_expected  INT,
    conf_p100_all           FLOAT,
    cps_p100_all            FLOAT,
    step_name               CHAR(20)
);
CREATE INDEX idx_test_confirmations_test_id_node_name ON test_confirmations (test_id,node_name);
alter table test_confirmations add column suite_id CHAR(64);


DROP TABLE IF EXISTS test_suiteinfo ;
CREATE TABLE test_suiteinfo (    
    test_env		CHAR(12),
    start_date      CHAR(22),
  	end_date        CHAR(22),
    test_name       VARCHAR,
    suite_id         CHAR(64)
);
CREATE INDEX idx_test_suiteinfo_suite_id ON test_suiteinfo (suite_id);
CREATE INDEX idx_test_suiteinfo_test_name ON test_suiteinfo (test_name);



--DROP TABLE IF EXISTS test_key_string ;
--CREATE TABLE test_key_string (
--    test_id             CHAR(64),
--    node_name           CHAR(32),
--    test_key            varchar,
--    test_value          varchar
--);
--CREATE INDEX idx_test_key_string_test_id_node_name
--ON test_key_string (test_id,node_name);