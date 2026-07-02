document.addEventListener("DOMContentLoaded", async () => {
    const currentUser = await AuthGuard.requireFreshUser();
    if (!currentUser) return;
    if (!AuthGuard.hasRole('Super Admin')) {
        document.body.innerHTML = '<h1 style="color:white;text-align:center;margin-top:50px;">Access Denied</h1>';
        return;
    }
    AuthGuard.setupSidebar();

    let admins = [];
    let permissions = [];

    const modal = document.getElementById('admin-modal');
    const form = document.getElementById('form-admin');
    const fields = document.getElementById('admin-fields');

    async function loadData() {
        [admins, permissions] = await Promise.all([
            AuthGuard.apiCall('/rbac/admins'),
            AuthGuard.apiCall('/rbac/permissions')
        ]);
        renderAdmins();
    }

    function renderAdmins() {
        const tbody = document.getElementById('admins-tbody');
        tbody.innerHTML = admins.map(admin => {
            const perms = admin.permissions.map(p => `<span class="role-badge">${p}</span>`).join(' ');
            return `
                <tr>
                    <td style="font-weight: 500;">${admin.name}</td>
                    <td>${admin.email}</td>
                    <td>${perms || '<span style="color: var(--text-muted);">None</span>'}</td>
                    <td><button class="btn-primary edit-admin" data-id="${admin.id}">Assign Permissions</button></td>
                </tr>
            `;
        }).join('');
        document.querySelectorAll('.edit-admin').forEach(btn => {
            btn.addEventListener('click', () => openModal(btn.dataset.id));
        });
    }

    function renderPermissions(admin = null) {
        document.getElementById('permissions-list').innerHTML = permissions.map(permission => `
            <label class="checkbox-label">
                <input type="checkbox" name="permissions" value="${permission.id}" ${admin && admin.permissions.includes(permission.permission_name) ? 'checked' : ''}>
                ${permission.permission_name}
            </label>
        `).join('');
    }

    function openModal(id = null) {
        form.reset();
        document.getElementById('a-msg').textContent = '';
        document.getElementById('a-id').value = id || '';
        const admin = admins.find(item => item.id == id);
        fields.style.display = id ? 'none' : 'block';
        document.getElementById('modal-title').textContent = id ? 'Assign Admin Permissions' : 'Create Admin';
        renderPermissions(admin);
        modal.classList.add('active');
    }

    document.getElementById('btn-create-admin').addEventListener('click', () => openModal());
    document.getElementById('btn-close-modal').addEventListener('click', () => modal.classList.remove('active'));

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const msg = document.getElementById('a-msg');
        msg.textContent = '';
        const permission_ids = Array.from(document.querySelectorAll('input[name="permissions"]:checked')).map(cb => Number.parseInt(cb.value, 10));
        const id = document.getElementById('a-id').value;

        try {
            let adminId = id;
            if (!id) {
                const password = document.getElementById('a-password').value;
                const confirm = document.getElementById('a-confirm').value;
                if (password !== confirm) {
                    msg.textContent = 'Passwords mismatch';
                    return;
                }
                const admin = await AuthGuard.apiCall('/rbac/admins', {
                    method: 'POST',
                    body: JSON.stringify({
                        name: document.getElementById('a-name').value,
                        email: document.getElementById('a-email').value,
                        password,
                        confirm_password: confirm,
                        role_ids: []
                    })
                });
                adminId = admin.id;
            }

            await AuthGuard.apiCall(`/rbac/admins/${adminId}/permissions`, {
                method: 'PUT',
                body: JSON.stringify({ permission_ids })
            });
            modal.classList.remove('active');
            await loadData();
        } catch (error) {
            msg.textContent = error.message;
        }
    });

    await loadData();
});
