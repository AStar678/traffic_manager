import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.Statement;
import java.util.regex.Pattern;

/**
 * Read-only production audit. It deliberately reports counts only and never
 * prints credentials, password values, or complete password hashes.
 */
public final class PasswordHashAudit {
    private static final Pattern BCRYPT = Pattern.compile(
            "^\\$2[aby]\\$\\d{2}\\$[./A-Za-z0-9]{53}$"
    );

    private PasswordHashAudit() {
    }

    public static void main(String[] args) throws Exception {
        String jdbcUrl = requiredEnvironment("DB_URL");
        String username = requiredEnvironment("DB_USERNAME");
        String password = requiredEnvironment("DB_PASSWORD");
        int total = 0;
        int compliant = 0;

        try (Connection connection = DriverManager.getConnection(jdbcUrl, username, password);
             Statement statement = connection.createStatement();
             ResultSet result = statement.executeQuery("SELECT password FROM `user`")) {
            while (result.next()) {
                total++;
                String storedPassword = result.getString(1);
                if (storedPassword != null && BCRYPT.matcher(storedPassword).matches()) {
                    compliant++;
                }
            }
        }

        int nonCompliant = total - compliant;
        System.out.printf(
                "users_total=%d bcrypt_compliant=%d non_bcrypt=%d%n",
                total,
                compliant,
                nonCompliant
        );
        if (nonCompliant != 0) {
            System.exit(2);
        }
    }

    private static String requiredEnvironment(String name) {
        String value = System.getenv(name);
        if (value == null || value.isBlank()) {
            throw new IllegalStateException("Missing environment variable: " + name);
        }
        return value;
    }
}
