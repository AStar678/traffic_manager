package com.visiondrive.migration;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

import javax.sql.DataSource;
import java.sql.Clob;
import java.sql.Connection;
import java.sql.DatabaseMetaData;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.ResultSetMetaData;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

@Slf4j
@Component
@RequiredArgsConstructor
@ConditionalOnProperty(name = "migration.h2.enabled", havingValue = "true")
public class H2ToMySqlMigrationRunner implements ApplicationRunner {

    private static final Map<String, String> TABLES = new LinkedHashMap<>();

    static {
        TABLES.put("APP_USER", "user");
        TABLES.put("ALERT_EVENT", "alert_event");
        TABLES.put("DETECTION_RESULT", "detection_result");
        TABLES.put("INFERENCE_RECORD", "inference_record");
        TABLES.put("JOB", "job");
        TABLES.put("OWNER_GESTURE_CONTROL_BINDING", "owner_gesture_control_binding");
        TABLES.put("SYSTEM_LOG", "system_log");
    }

    private final DataSource targetDataSource;

    @Value("${migration.h2.url}")
    private String sourceUrl;

    @Override
    public void run(ApplicationArguments arguments) throws Exception {
        try (Connection source = DriverManager.getConnection(sourceUrl, "sa", "");
             Connection target = targetDataSource.getConnection()) {
            target.setAutoCommit(false);
            try {
                for (Map.Entry<String, String> table : TABLES.entrySet()) {
                    copyTable(source, target, table.getKey(), table.getValue());
                }
                target.commit();
                log.info("H2 到 MySQL 数据迁移完成");
            } catch (Exception exception) {
                target.rollback();
                throw exception;
            }
        }
    }

    private void copyTable(Connection source, Connection target, String sourceTable, String targetTable)
            throws SQLException {
        long targetCount = countRows(target, targetTable);
        if (targetCount > 0) {
            throw new IllegalStateException("目标表非空，拒绝重复迁移: " + targetTable);
        }

        Set<String> targetColumns = readTargetColumns(target, targetTable);
        try (Statement statement = source.createStatement();
             ResultSet rows = statement.executeQuery("SELECT * FROM \"" + sourceTable + "\"")) {
            ResultSetMetaData metadata = rows.getMetaData();
            List<String> sourceColumns = new ArrayList<>();
            for (int index = 1; index <= metadata.getColumnCount(); index++) {
                String column = metadata.getColumnLabel(index);
                if (targetColumns.contains(column.toLowerCase(Locale.ROOT))) {
                    sourceColumns.add(column);
                }
            }

            if (sourceColumns.isEmpty()) {
                log.warn("表没有可迁移的公共字段: {} -> {}", sourceTable, targetTable);
                return;
            }

            String columnsSql = sourceColumns.stream()
                    .map(column -> quote(column.toLowerCase(Locale.ROOT)))
                    .collect(Collectors.joining(", "));
            String parametersSql = sourceColumns.stream().map(column -> "?")
                    .collect(Collectors.joining(", "));
            String insertSql = "INSERT INTO " + quote(targetTable) + " (" + columnsSql + ") VALUES ("
                    + parametersSql + ")";

            int copied = 0;
            try (PreparedStatement insert = target.prepareStatement(insertSql)) {
                while (rows.next()) {
                    for (int index = 0; index < sourceColumns.size(); index++) {
                        Object value = rows.getObject(sourceColumns.get(index));
                        if (value instanceof Clob clob) {
                            value = clob.getSubString(1, Math.toIntExact(clob.length()));
                        }
                        insert.setObject(index + 1, value);
                    }
                    insert.addBatch();
                    copied++;
                    if (copied % 500 == 0) insert.executeBatch();
                }
                insert.executeBatch();
            }
            log.info("迁移表完成: {} -> {}, rows={}", sourceTable, targetTable, copied);
        }
    }

    private long countRows(Connection connection, String table) throws SQLException {
        try (Statement statement = connection.createStatement();
             ResultSet result = statement.executeQuery("SELECT COUNT(*) FROM " + quote(table))) {
            result.next();
            return result.getLong(1);
        }
    }

    private Set<String> readTargetColumns(Connection connection, String table) throws SQLException {
        DatabaseMetaData metadata = connection.getMetaData();
        Set<String> columns = new LinkedHashSet<>();
        try (ResultSet result = metadata.getColumns(connection.getCatalog(), null, table, null)) {
            while (result.next()) {
                columns.add(result.getString("COLUMN_NAME").toLowerCase(Locale.ROOT));
            }
        }
        return columns;
    }

    private String quote(String identifier) {
        return "`" + identifier.replace("`", "``") + "`";
    }
}
