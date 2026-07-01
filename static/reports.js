document.addEventListener("DOMContentLoaded", async () => {
    const currentUser = await AuthGuard.requireFreshUser();
    if (!currentUser) return;
    if (!AuthGuard.hasPermission('view_reports')) {
        document.body.innerHTML = '<h1 style="color:white;text-align:center;margin-top:50px;">Access Denied</h1>';
        return;
    }
    AuthGuard.setupSidebar();

    try {
        const data = await AuthGuard.apiCall('/rbac/reports');
        
        const rows = [
            ...data.items,
            ...(data.recent_activity || []).map(item => ({ name: `Recent Activity: ${item.name}`, value: item.value }))
        ];
        document.getElementById('reports-tbody').innerHTML = rows.map(item => `
            <tr>
                <td>${item.name}</td>
                <td>${item.value}</td>
            </tr>
        `).join('');

    } catch (e) {
        console.error(e);
        document.getElementById('reports-tbody').innerHTML = '<tr><td colspan="2">Failed to load reports.</td></tr>';
    }
});
