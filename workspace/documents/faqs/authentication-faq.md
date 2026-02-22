# Authentication FAQ

## Password Reset

If you've forgotten your DataStack account password, you can reset it through the authentication page:

1. Go to app.datastack.io/login.
2. Click **Forgot Password**.
3. Enter the email address associated with your DataStack authentication account.
4. Check your inbox for a password reset link (valid for 24 hours).
5. Click the link and set a new password.

Passwords must be at least 12 characters and include a mix of uppercase, lowercase, numbers, and symbols. Authentication credentials are hashed with bcrypt and never stored in plaintext.

If you don't receive the authentication reset email, check your spam folder. Enterprise accounts using SSO authentication should contact their IT admin instead — password resets are managed by the identity provider.

## Two-Factor Setup

Strengthen your authentication security with two-factor authentication (2FA):

1. Go to **Settings > Security** in the DataStack dashboard.
2. Click **Enable Two-Factor Authentication**.
3. Scan the QR code with an authenticator app (Google Authenticator, Authy, or 1Password).
4. Enter the 6-digit authentication code to confirm setup.

Once enabled, you'll need both your password and a 2FA code for authentication on every login. Backup codes are provided during setup — store them securely in case you lose access to your authentication device.

Two-factor authentication is required for all admin users on Enterprise plans. Team owners can enforce 2FA authentication for all workspace members in the security settings.

## Account Lockout

After 5 consecutive failed authentication attempts, your account is locked for 30 minutes. This protects against brute-force authentication attacks.

If your account is locked:

- **Wait 30 minutes** and try again with the correct authentication credentials.
- **Reset your password** if you've forgotten it (the reset flow bypasses the lockout).
- **Contact support** if you believe your authentication account has been compromised.

Enterprise accounts can customize lockout thresholds (3–10 attempts) and lockout duration (15–120 minutes) in the authentication security settings.
