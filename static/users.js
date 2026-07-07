document.addEventListener("DOMContentLoaded", async () => {
    const currentUser = await AuthGuard.requireFreshUser();
    if (!currentUser) return;
    if (!AuthGuard.hasPermission('view_user')) {
        document.body.innerHTML = '<h1 style="color:white;text-align:center;margin-top:50px;">Access Denied</h1>';
        return;
    }
    AuthGuard.setupSidebar();

    let allRoles = [];
    let usersList = [];

    async function loadData() {
        try {
            usersList = await AuthGuard.apiCall('/rbac/users');
            allRoles = AuthGuard.hasPermission('manage_roles')
                ? await AuthGuard.apiCall('/rbac/roles')
                : [];
            renderUsers();
        } catch(e) {
            console.error(e);
            document.getElementById('users-tbody').innerHTML = '<tr><td colspan="5">Failed to load data.</td></tr>';
        }
    }

    function renderUsers() {
        const tbody = document.getElementById('users-tbody');
        tbody.innerHTML = '';
        
        usersList.forEach(u => {
            const tr = document.createElement('tr');
            
            const rolesHtml = u.roles.map(r => `<span class="role-badge">${r}</span>`).join(' ');
            const statusHtml = u.is_active ? 
                `<span style="color: var(--success);">Active</span>` : 
                `<span style="color: var(--danger);">Inactive</span>`;
            
            const actions = [];
            if (AuthGuard.hasPermission('edit_user')) {
                actions.push(`<button class="btn-ghost edit-btn" data-id="${u.id}">Edit</button>`);
            }
            if (AuthGuard.hasPermission('delete_user') && u.id !== currentUser.id) {
                actions.push(`<button class="btn-danger delete-btn" data-id="${u.id}">Delete</button>`);
            }

            tr.innerHTML = `
                <td style="font-weight: 500;">${u.name}</td>
                <td>${u.email}</td>
                <td>${rolesHtml}</td>
                <td>${statusHtml}</td>
                <td>${actions.join(' ')}</td>
            `;
            tbody.appendChild(tr);
        });

        document.querySelectorAll('.edit-btn').forEach(btn => btn.addEventListener('click', (e) => openModal(e.target.dataset.id)));
        document.querySelectorAll('.delete-btn').forEach(btn => btn.addEventListener('click', (e) => deleteUser(e.target.dataset.id)));
    }

    // Modal logic
    const modal = document.getElementById('user-modal');
    const form = document.getElementById('form-user');
    const roleListDiv = document.getElementById('roles-list');

    function populateRolesList() {
        if (!AuthGuard.hasPermission('manage_roles')) {
            roleListDiv.innerHTML = '<span style="color: var(--text-muted);">New users are created with the User role.</span>';
            return;
        }
        roleListDiv.innerHTML = allRoles.map(r => `
            <label class="checkbox-label">
                <input type="checkbox" name="roles" value="${r.id}"> ${r.role_name}
            </label>
        `).join('');
    }

    function openModal(id = null) {
        populateRolesList();
        const msg = document.getElementById('u-msg');
        msg.textContent = '';
        form.reset();
        
        const pwdGroup = document.getElementById('pwd-group');
        const pwdConfirmGroup = document.getElementById('pwd-confirm-group');
        
        if (id) {
            document.getElementById('modal-title').textContent = 'Edit User';
            pwdGroup.style.display = 'none';
            pwdConfirmGroup.style.display = 'none';
            document.getElementById('u-password').required = false;
            document.getElementById('u-confirm').required = false;

            const u = usersList.find(x => x.id == id);
            document.getElementById('u-id').value = u.id;
            document.getElementById('u-name').value = u.name;
            document.getElementById('u-email').value = u.email;
            document.getElementById('u-active').checked = u.is_active;
            
            const roleIds = new Set(allRoles.filter(r => u.roles.includes(r.role_name)).map(r => r.id.toString()));
            document.querySelectorAll('input[name="roles"]').forEach(cb => {
                cb.checked = roleIds.has(cb.value);
            });
        } else {
            document.getElementById('modal-title').textContent = 'Create User';
            pwdGroup.style.display = 'block';
            pwdConfirmGroup.style.display = 'block';
            document.getElementById('u-password').required = true;
            document.getElementById('u-confirm').required = true;
            document.getElementById('u-id').value = '';
        }
        
        modal.classList.add('active');
    }

    document.getElementById('btn-close-modal').addEventListener('click', () => modal.classList.remove('active'));
    
    const btnCreate = document.getElementById('btn-create-user');
    if (btnCreate && AuthGuard.hasPermission('create_user')) {
        btnCreate.addEventListener('click', () => openModal(null));
    } else if (btnCreate) {
        btnCreate.style.display = 'none';
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const msg = document.getElementById('u-msg');
        msg.textContent = '';
        
        const id = document.getElementById('u-id').value;
        const name = document.getElementById('u-name').value;
        const email = document.getElementById('u-email').value;
        const is_active = document.getElementById('u-active').checked;
        const role_ids = AuthGuard.hasPermission('manage_roles')
            ? Array.from(document.querySelectorAll('input[name="roles"]:checked')).map(cb => Number.parseInt(cb.value, 10))
            : [];

        try {
            if (id) {
                // Update
                await AuthGuard.apiCall(`/rbac/users/${id}`, {
                    method: 'PUT',
                    body: JSON.stringify({ name, email, is_active, role_ids })
                });
            } else {
                // Create
                const pwd = document.getElementById('u-password').value;
                const conf = document.getElementById('u-confirm').value;
                if(pwd !== conf) { msg.textContent="Passwords mismatch"; return; }
                
                await AuthGuard.apiCall('/rbac/users', {
                    method: 'POST',
                    body: JSON.stringify({ name, email, password: pwd, confirm_password: conf, role_ids })
                });
            }
            modal.classList.remove('active');
            loadData();
        } catch (err) {
            msg.textContent = err.message;
        }
    });

    async function deleteUser(id) {
        if(!confirm("Are you sure you want to delete this user?")) return;
        try {
            await AuthGuard.apiCall(`/rbac/users/${id}`, { method: 'DELETE' });
            loadData();
        } catch (e) { alert(e.message); }
    }

    loadData();
});

