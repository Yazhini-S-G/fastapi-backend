document.addEventListener("DOMContentLoaded", async () => {
    const currentUser = await AuthGuard.requireFreshUser();
    if (!currentUser) return;
    if (!AuthGuard.hasPermission('manage_roles')) {
        document.body.innerHTML = '<h1 style="color:white;text-align:center;margin-top:50px;">Access Denied</h1>';
        return;
    }
    AuthGuard.setupSidebar();

    let allRoles = [];
    let allPermissions = [];

    async function loadData() {
        try {
            [allRoles, allPermissions] = await Promise.all([
                AuthGuard.apiCall('/rbac/roles'),
                AuthGuard.apiCall('/rbac/permissions')
            ]);
            renderRoles();
        } catch(e) {
            console.error(e);
            document.getElementById('roles-tbody').innerHTML = '<tr><td colspan="5">Failed to load data.</td></tr>';
        }
    }

    function renderRoles() {
        const tbody = document.getElementById('roles-tbody');
        tbody.innerHTML = '';
        
        allRoles.forEach(r => {
            const tr = document.createElement('tr');
            
            const permsHtml = r.permissions.map(p => `<span class="role-badge" style="margin-bottom: 4px; display: inline-block; margin-right: 4px; background: rgba(16, 185, 129, 0.1); color: var(--success);">${p}</span>`).join('');
            
            tr.innerHTML = `
                <td>${r.id}</td>
                <td style="font-weight: 500;">${r.role_name}</td>
                <td>${r.description}</td>
                <td>${permsHtml || '<span style="color:var(--text-muted)">None</span>'}</td>
                <td><button class="btn-primary edit-btn" data-id="${r.id}">Edit</button></td>
            `;
            tbody.appendChild(tr);
        });

        document.querySelectorAll('.edit-btn').forEach(btn => btn.addEventListener('click', (e) => openModal(e.target.dataset.id)));
    }

    // Modal logic
    const modal = document.getElementById('role-modal');
    const form = document.getElementById('form-role');
    const permListDiv = document.getElementById('permissions-list');

    function openModal(id = null) {
        const role = allRoles.find(x => x.id == id) ?? null;
        if(id && !role) return;

        document.getElementById('modal-title').textContent = id ? 'Edit Role' : 'Create Role';
        document.getElementById('r-id').value = role?.id ?? '';
        document.getElementById('r-name').value = role?.role_name ?? '';
        document.getElementById('r-name').disabled = !!role;
        document.getElementById('r-desc').value = role?.description ?? '';
        document.getElementById('r-msg').textContent = '';

        permListDiv.innerHTML = allPermissions.map(p => `
            <label class="checkbox-label">
                <input type="checkbox" name="permissions" value="${p.id}" ${role && role.permissions.includes(p.permission_name) ? 'checked' : ''}>
                ${p.permission_name} <span style="color: var(--text-muted); font-size: 0.8rem;">- ${p.description}</span>
            </label>
        `).join('');
        
        modal.classList.add('active');
    }

    document.getElementById('btn-close-modal').addEventListener('click', () => modal.classList.remove('active'));
    document.getElementById('btn-create-role').addEventListener('click', () => openModal());

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const msg = document.getElementById('r-msg');
        msg.textContent = '';
        
        const id = document.getElementById('r-id').value;
        const role_name = document.getElementById('r-name').value;
        const description = document.getElementById('r-desc').value;
        const permission_ids = Array.from(document.querySelectorAll('input[name="permissions"]:checked')).map(cb => Number.parseInt(cb.value, 10));

        try {
            if (id) {
                await AuthGuard.apiCall(`/rbac/roles/${id}`, {
                    method: 'PUT',
                    body: JSON.stringify({ description, permission_ids })
                });
            } else {
                await AuthGuard.apiCall('/rbac/roles', {
                    method: 'POST',
                    body: JSON.stringify({ role_name, description, permission_ids })
                });
            }
            modal.classList.remove('active');
            loadData();
        } catch (err) {
            msg.textContent = err.message;
        }
    });

    loadData();
});

