package in.pramalex.api;

import org.springframework.boot.CommandLineRunner;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;

/**
 * Local demo-account bootstrap.
 * Creates the three requested accounts when missing. Existing passwords are
 * preserved; existing roles/statuses are corrected to the intended demo roles.
 * Change demo credentials before deployment.
 */
@Component
class DemoAccountBootstrap implements CommandLineRunner {
    private final JdbcTemplate jdbc;
    private final PasswordEncoder encoder;

    DemoAccountBootstrap(JdbcTemplate jdbc, PasswordEncoder encoder) {
        this.jdbc = jdbc;
        this.encoder = encoder;
    }

    @Override
    public void run(String... args) {
        ensureAccount("admin@pramalex.local", "PramaLex Administrator", "ADMIN");
        ensureAccount("lawyer@pramalex.local", "PramaLex Lawyer", "LAWYER");
        ensureAccount("public@pramalex.local", "PramaLex Public User", "PUBLIC");
        System.out.println("PramaLex demo accounts checked: admin, lawyer, public.");
    }

    private void ensureAccount(String email, String name, String role) {
        Integer count = jdbc.queryForObject(
            "SELECT COUNT(*) FROM users WHERE email = ?",
            Integer.class, email
        );
        if (count != null && count > 0) {
            jdbc.update(
                "UPDATE users SET full_name = ?, role = ?, status = 'ACTIVE' WHERE email = ?",
                name, role, email
            );
        } else {
            jdbc.update(
                "INSERT INTO users (email, full_name, password_hash, role, status, created_at) " +
                "VALUES (?, ?, ?, ?, 'ACTIVE', NOW(6))",
                email, name, encoder.encode("Sjt@12345678"), role
            );
        }
    }
}
