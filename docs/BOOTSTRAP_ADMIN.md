# Demo accounts and administrator bootstrap

On startup, `DemoAccountBootstrap` creates these local demo accounts if they do not exist:

| Role | Email | Default password |
|---|---|---|
| ADMIN | admin@pramalex.local | Sjt@12345678 |
| LAWYER | lawyer@pramalex.local | Sjt@12345678 |
| PUBLIC | public@pramalex.local | Sjt@12345678 |

Passwords are stored as BCrypt hashes. Existing accounts keep their existing password; the bootstrap corrects their role, display name, and active status. If an account already existed before this bootstrap was added and you need the default password, reset that account deliberately using a BCrypt hash or remove that demo account and restart the app.

Verify with:

```sql
USE pramalex;
SELECT email, role, status FROM users
WHERE email IN ('admin@pramalex.local','lawyer@pramalex.local','public@pramalex.local');
```

These are development/demo credentials. Change them before deployment and do not expose the application publicly while they are active.
