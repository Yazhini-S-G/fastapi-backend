document.addEventListener("DOMContentLoaded", async () => {
    const user = await AuthGuard.requireFreshUser();
    if (!user) return;

    AuthGuard.setupSidebar();

    // Fill profile info
    document.getElementById('profile-avatar').textContent = user.name.charAt(0).toUpperCase();
    document.getElementById('profile-name').textContent = user.name;
    document.getElementById('profile-email').textContent = user.email;
    document.getElementById('profile-role-badge').textContent = user.roles.join(', ') || 'User';
    document.getElementById('profile-status').textContent = user.is_active ? 'Active' : 'Inactive';

    // Change Password
    document.getElementById('form-change-pwd').addEventListener('submit', async (e) => {
        e.preventDefault();
        const msg = document.getElementById('cp-msg');
        msg.textContent = '';
        msg.style.color = 'var(--text-main)';

        const op = document.getElementById('cp-old').value;
        const np = document.getElementById('cp-new').value;
        const cp = document.getElementById('cp-confirm').value;

        if (np !== cp) {
            msg.textContent = 'New passwords do not match';
            msg.style.color = 'var(--danger)';
            return;
        }

        try {
            await AuthGuard.apiCall('/auth/change-password', {
                method: 'POST',
                body: JSON.stringify({
                    old_password: op,
                    new_password: np,
                    confirm_password: cp
                })
            });
            msg.textContent = 'Password changed successfully.';
            msg.style.color = 'var(--success)';
            e.target.reset();
        } catch (err) {
            msg.textContent = err.message;
            msg.style.color = 'var(--danger)';
        }
    });

    // Reset Password
    document.getElementById('form-reset-pwd').addEventListener('submit', async (e) => {
        e.preventDefault();
        const msg = document.getElementById('rp-msg');
        msg.textContent = '';

        const tk = document.getElementById('rp-token').value;
        const np = document.getElementById('rp-new').value;
        const cp = document.getElementById('rp-confirm').value;

        if (np !== cp) {
            msg.textContent = 'Passwords do not match';
            msg.style.color = 'var(--danger)';
            return;
        }

        try {
            await AuthGuard.apiCall('/auth/reset-password', {
                method: 'POST',
                body: JSON.stringify({
                    reset_token: tk,
                    new_password: np,
                    confirm_password: cp
                })
            });
            msg.textContent = 'Password reset successfully.';
            msg.style.color = 'var(--success)';
            e.target.reset();
        } catch (err) {
            msg.textContent = err.message;
            msg.style.color = 'var(--danger)';
        }
    });
});
