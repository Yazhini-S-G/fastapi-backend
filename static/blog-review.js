function imageUrl(path) {
    if (!path) {
        return "";
    }

    return path.startsWith("http")
        ? path
        : `${AuthGuard.BASE_URL}${path}`;
}

function stripHtml(html) {
    const div = document.createElement("div");
    div.textContent = html;
    return div.textContent;
}

function dashboardPath() {
    globalThis.window.location.href = AuthGuard.dashboardFor();
}

document.addEventListener("DOMContentLoaded", async () => {
    const currentUser = await AuthGuard.requireFreshUser();
    if (!currentUser) return;
    if (!AuthGuard.hasPermission("review_blog") && !AuthGuard.hasPermission("publish_blog")) {
        document.body.innerHTML = '<h1 style="color:white;text-align:center;margin-top:50px;">Access Denied</h1>';
        return;
    }
    AuthGuard.setupSidebar();
    document.getElementById("nav-dashboard").addEventListener("click", dashboardPath);

    let blogs = [];

    async function loadReview() {
        const params = new URLSearchParams();
        const search = document.getElementById("review-search").value.trim();
        const status = document.getElementById("review-status").value;
        if (search) params.set("search", search);
        if (status) params.set("status_filter", status);
        const queryString = params.toString();
        blogs = await AuthGuard.apiCall(queryString ? `/blogs?${queryString}` : "/blogs");
        renderReview();
    }

    function renderReview() {
        const list = document.getElementById("review-list");
        if (blogs.length === 0) {
            list.innerHTML = '<div class="glass blog-card">No blogs need review.</div>';
            return;
        }

        list.innerHTML = blogs.map(blog => {
            const featuredImageHtml = blog.featured_image
                ? `<img src="${imageUrl(blog.featured_image)}" class="blog-thumb" alt="">`
                : "";
            const categoryName = blog.category_name || "Uncategorized";
            const blogMeta = `By ${blog.author_name} · ${categoryName} · ${new Date(blog.created_at).toLocaleDateString()}`;
            const reviewActions = AuthGuard.hasPermission("review_blog")
                ? `<button class="btn-ghost set-status" data-id="${blog.id}" data-status="Pending Review">Approve</button><button class="btn-danger set-status" data-id="${blog.id}" data-status="Rejected">Reject</button>`
                : "";
            const publishAction = AuthGuard.hasPermission("publish_blog")
                ? `<button class="btn-primary set-status" data-id="${blog.id}" data-status="Published">Publish</button>`
                : "";
            const featureAction = AuthGuard.hasPermission("feature_blog")
                ? `<button class="btn-ghost feature-blog" data-id="${blog.id}">${blog.is_featured ? "Unfeature" : "Feature"}</button>`
                : "";
            const deleteAction = AuthGuard.hasPermission("delete_blog")
                ? `<button class="btn-danger delete-blog" data-id="${blog.id}">Delete</button>`
                : "";

            return `
            <article class="glass blog-card">
                ${featuredImageHtml}
                <div class="blog-card-body">
                    <div class="badge badge-warning">${blog.status}</div>
                    <h3>${blog.title}</h3>
                    <div class="blog-meta">${blogMeta}</div>
                    <p>${stripHtml(blog.content).slice(0, 220)}</p>
                    <div class="action-row">
                        ${reviewActions}
                        ${publishAction}
                        ${featureAction}
                        ${deleteAction}
                    </div>
                </div>
            </article>
        `;
        }).join("");

        document.querySelectorAll(".set-status").forEach(btn => btn.addEventListener("click", () => setStatus(btn.dataset.id, btn.dataset.status)));
        document.querySelectorAll(".feature-blog").forEach(btn => btn.addEventListener("click", () => featureBlog(btn.dataset.id)));
        document.querySelectorAll(".delete-blog").forEach(btn => btn.addEventListener("click", () => deleteBlog(btn.dataset.id)));
    }

    async function setStatus(id, status) {
        await AuthGuard.apiCall(`/blogs/${id}/status`, { method: "PUT", body: JSON.stringify({ status }) });
        await loadReview();
    }

    async function featureBlog(id) {
        await AuthGuard.apiCall(`/blogs/${id}/feature`, { method: "PUT" });
        await loadReview();
    }

    async function deleteBlog(id) {
        if (!confirm("Delete this blog?")) return;
        await AuthGuard.apiCall(`/blogs/${id}`, { method: "DELETE" });
        await loadReview();
    }

    ["review-search", "review-status"].forEach(id => document.getElementById(id).addEventListener("input", loadReview));
    await loadReview();
});

