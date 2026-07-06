document.addEventListener("DOMContentLoaded", async () => {
    if (AuthGuard.getToken()) {
        const user = AuthGuard.getUser();
        if (!user) {
            await AuthGuard.fetchUser();
        }
        const currentUser = AuthGuard.getUser();
        if (currentUser) {
            if (currentUser.roles.includes('Super Admin')) {
                window.location.href = '/superadmin.html';
            } else if (currentUser.roles.includes('Admin')) {
                window.location.href = '/admin.html';
            } else {
                window.location.href = '/dashboard.html';
            }
        }
        return;
    }

    const tabLogin = document.getElementById('tab-login');
    const tabRegister = document.getElementById('tab-register');
    const formLogin = document.getElementById('form-login');
    const formRegister = document.getElementById('form-register');

    tabLogin.addEventListener('click', () => {
        tabLogin.classList.add('active');
        tabRegister.classList.remove('active');
        formLogin.classList.remove('hidden');
        formRegister.classList.add('hidden');
    });

    tabRegister.addEventListener('click', () => {
        tabRegister.classList.add('active');
        tabLogin.classList.remove('active');
        formRegister.classList.remove('hidden');
        formLogin.classList.add('hidden');
    });

    formLogin.addEventListener('submit', async (e) => {
        e.preventDefault();
        const errDiv = document.getElementById('login-error');
        errDiv.textContent = '';
        
        try {
            const data = await AuthGuard.apiCall('/auth/login', {
                method: 'POST',
                body: JSON.stringify({
                    email: document.getElementById('login-email').value,
                    password: document.getElementById('login-password').value
                })
            });
            AuthGuard.setToken(data.access_token);
            const user = await AuthGuard.fetchUser();
            
            if (user?.roles.includes('Super Admin')) {
                window.location.href = '/superadmin.html';
            } else if (user?.roles.includes('Admin')) {
                window.location.href = '/admin.html';
            } else {
                window.location.href = '/dashboard.html';
            }
        } catch (err) {
            errDiv.textContent = err.message;
        }
    });

    formRegister.addEventListener('submit', async (e) => {
        e.preventDefault();
        const errDiv = document.getElementById('reg-error');
        errDiv.textContent = '';

        const pwd = document.getElementById('reg-password').value;
        const confirm = document.getElementById('reg-confirm').value;

        if (pwd !== confirm) {
            errDiv.textContent = 'Passwords do not match';
            return;
        }
        
        try {
            await AuthGuard.apiCall('/auth/register', {
                method: 'POST',
                body: JSON.stringify({
                    name: document.getElementById('reg-name').value,
                    email: document.getElementById('reg-email').value,
                    password: pwd,
                    confirm_password: confirm
                })
            });
            alert('Registration successful! You can now sign in.');
            tabLogin.click();
        } catch (err) {
            errDiv.textContent = err.message;
        }
    });
});
