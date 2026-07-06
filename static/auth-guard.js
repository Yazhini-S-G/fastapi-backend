class AuthGuard {
    static BASE_URL = 'http://127.0.0.1:8000';

    static getToken() {
        return localStorage.getItem('access_token');
    }

    static setToken(token) {
        localStorage.setItem('access_token', token);
    }

    static clearToken() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user_data');
    }

    static getUser() {
        const data = localStorage.getItem('user_data');
        return data ? JSON.parse(data) : null;
    }

    static setUser(user) {
        localStorage.setItem('user_data', JSON.stringify(user));
    }

    static hasPermission(permissionName) {
        const user = this.getUser();
        if (!user) return false;
        if (user.roles?.includes('Super Admin')) return true;
        return user.permissions?.includes(permissionName);
    }

    static hasRole(roleName) {
        const user = this.getUser();
        return !!user?.roles?.includes(roleName);
    }

    static dashboardFor(user = this.getUser()) {
        if (user?.roles.includes('Super Admin')) return '/superadmin.html';
        if (user?.roles.includes('Admin')) return '/admin.html';
        return '/dashboard.html';
    }

    static requireAuth() {
        if (!this.getToken()) {
            window.location.href = '/index.html';
        }
    }

    static async fetchUser() {
        const token = this.getToken();
        if (!token) return null;

        try {
            const res = await fetch(`${this.BASE_URL}/rbac/me`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                const user = await res.json();
                this.setUser(user);
                return user;
            } else {
                this.clearToken();
                window.location.href = '/index.html';
            }
        } catch (e) {
            console.error(e);
        }
        return null;
    }

    static async requireFreshUser() {
        this.requireAuth();
        const user = await this.fetchUser();
        return user;
    }

    static async apiCall(endpoint, options) {
        const token = this.getToken();
        const requestOptions = options ?? {};
        const isFormData = requestOptions.body instanceof FormData;
        const headers = {
            ...(!isFormData && { 'Content-Type': 'application/json' }),
            ...(token && { 'Authorization': `Bearer ${token}` }),
            ...(requestOptions.headers || {})
        };

        const response = await fetch(`${this.BASE_URL}${endpoint}`, {
            mode: 'cors',
            ...requestOptions,
            headers
        });

        if (response.status === 401) {
            this.clearToken();
            window.location.href = '/index.html';
            throw new Error("Unauthorized");
        }
        if (response.status === 403) {
            alert("Access Denied");
            throw new Error("Forbidden");
        }

        const data = await response.json().catch(() => null);
        if (!response.ok) {
            throw new Error(data?.detail || "API Error");
        }
        return data;
    }

    static setupSidebar() {
        const user = this.getUser();
        if (!user) return;
        this.ensureBlogNavigation();

        // Populate avatar & info
        const avatarEl = document.getElementById('topbar-avatar');
        const nameEl = document.getElementById('topbar-name');
        const roleEl = document.getElementById('topbar-role');

        if(avatarEl) avatarEl.textContent = user.name.charAt(0).toUpperCase();
        if(nameEl) nameEl.textContent = user.name;
        if(roleEl && user.roles.length > 0) roleEl.textContent = user.roles.join(', ');

        // Guard menu items
        document.querySelectorAll('[data-permission]').forEach(el => {
            const perm = el.dataset.permission;
            if (perm && !this.hasPermission(perm)) {
                el.style.display = 'none';
            }
        });

        // Setup logout
        const logoutBtn = document.getElementById('btn-logout');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', async () => {
                try {
                    await this.apiCall('/auth/logout', { method: 'POST' });
                } catch(e) {
                    console.error('Logout request failed', e);
                }
                this.clearToken();
                window.location.href = '/index.html';
            });
        }
    }

    static ensureBlogNavigation() {
        const nav = document.querySelector('.sidebar-nav');
        if (!nav || nav.querySelector('a[href="/blogs.html"]')) return;
        const profileLink = nav.querySelector('a[href="/profile.html"]');
        const blogsLink = document.createElement('a');
        blogsLink.href = '/blogs.html';
        blogsLink.className = 'nav-item';
        blogsLink.dataset.permission = 'create_blog';
        blogsLink.textContent = 'Blogs';
        const reviewLink = document.createElement('a');
        reviewLink.href = '/blog-review.html';
        reviewLink.className = 'nav-item';
        reviewLink.dataset.permission = 'review_blog';
        reviewLink.textContent = 'Blog Review';
        profileLink.before(blogsLink);
        profileLink.before(reviewLink);
    }
}

window.AuthGuard = AuthGuard;
