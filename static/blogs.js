document.addEventListener("DOMContentLoaded", async () => {
    const currentUser = await AuthGuard.requireFreshUser();
    if (!currentUser) return;
    if (!AuthGuard.hasPermission("create_blog")) {
        document.body.innerHTML = '<h1 style="color:white;text-align:center;margin-top:50px;">Access Denied</h1>';
        return;
    }
    AuthGuard.setupSidebar();

    let blogs = [];
    let categories = [];
    const modal = document.getElementById("blog-modal");
    const form = document.getElementById("blog-form");
    const msg = document.getElementById("blog-msg");

    function dashboardPath() {
        window.location.href = AuthGuard.dashboardFor();
    }

    document.getElementById("nav-dashboard").addEventListener("click", dashboardPath);

    async function loadCategories() {
        categories = await AuthGuard.apiCall("/blogs/categories");
        const options = ['<option value="">Uncategorized</option>', ...categories.map(c => `<option value="${c.id}">${c.name}</option>`)].join("");
        document.getElementById("blog-category").innerHTML = '<option value="">All Categories</option>' + categories.map(c => `<option value="${c.id}">${c.name}</option>`).join("");
        document.getElementById("blog-form-category").innerHTML = options;
    }

    async function loadAnalytics() {
        if (!AuthGuard.hasPermission("view_blog_analytics")) {
            document.getElementById("blog-stats").innerHTML = "";
            return;
        }
        const data = await AuthGuard.apiCall("/blogs/analytics");
        document.getElementById("blog-stats").innerHTML = [
            ["Total Blogs", data.total_blogs],
            ["Published", data.published_blogs],
            ["Pending", data.pending_blogs],
            ["Rejected", data.rejected_blogs],
        ].map(([label, value]) => `<div class="glass stat-card"><div class="stat-title">${label}</div><div class="stat-value">${value}</div></div>`).join("");
    }

    async function loadBlogs() {
        const params = new URLSearchParams();
        const search = document.getElementById("blog-search").value.trim();
        const status = document.getElementById("blog-status").value;
        const category = document.getElementById("blog-category").value;
        if (search) params.set("search", search);
        if (status) params.set("status_filter", status);
        if (category) params.set("category_id", category);
        blogs = await AuthGuard.apiCall(`/blogs${params.toString() ? `?${params}` : ""}`);
        renderBlogs();
    }

    function imageUrl(path) {
        if (!path) return "";
        return path.startsWith("http") ? path : `${AuthGuard.BASE_URL}${path}`;
    }

    function renderBlogs() {
        const list = document.getElementById("blogs-list");
        if (!blogs.length) {
            list.innerHTML = '<div class="glass blog-card">No blogs found.</div>';
            return;
        }
        list.innerHTML = blogs.map(blog => `
            <article class="glass blog-card">
                ${blog.featured_image ? `<img src="${imageUrl(blog.featured_image)}" class="blog-thumb" alt="">` : ""}
                <div class="blog-card-body">
                    <div class="badge badge-primary">${blog.status}</div>
                    <h3>${blog.title}</h3>
                    <p>${blog.content.replace(/<[^>]+>/g, "").slice(0, 140)}</p>
                    <div class="blog-meta">${blog.category_name || "Uncategorized"} · ${blog.tags || "No tags"}</div>
                    <div class="action-row">
                        ${AuthGuard.hasPermission("edit_blog") || blog.author_id === currentUser.id ? `<button class="btn-ghost edit-blog" data-id="${blog.id}">Edit</button>` : ""}
                        ${AuthGuard.hasPermission("delete_blog") ? `<button class="btn-danger delete-blog" data-id="${blog.id}">Delete</button>` : ""}
                    </div>
                </div>
            </article>
        `).join("");
        document.querySelectorAll(".edit-blog").forEach(btn => btn.addEventListener("click", () => openModal(btn.dataset.id)));
        document.querySelectorAll(".delete-blog").forEach(btn => btn.addEventListener("click", () => deleteBlog(btn.dataset.id)));
    }

    function openModal(id = "") {
        form.reset();
        msg.textContent = "";
        document.getElementById("featured-image-path").value = "";
        document.getElementById("image-preview").classList.add("hidden");
        const blog = id ? blogs.find(item => item.id == id) : null;
        document.getElementById("blog-modal-title").textContent = blog ? "Edit Blog" : "Create Blog";
        document.getElementById("blog-id").value = blog ? blog.id : "";
        if (blog) {
            document.getElementById("blog-title").value = blog.title;
            document.getElementById("blog-content").value = blog.content;
            document.getElementById("blog-form-category").value = blog.category_id || "";
            document.getElementById("blog-tags").value = blog.tags || "";
            document.getElementById("featured-image-path").value = blog.featured_image || "";
            if (blog.featured_image) {
                const preview = document.getElementById("image-preview");
                preview.src = imageUrl(blog.featured_image);
                preview.classList.remove("hidden");
            }
        }
        modal.classList.add("active");
    }

    async function uploadImageIfNeeded() {
        const input = document.getElementById("blog-image");
        if (!input.files.length) return document.getElementById("featured-image-path").value || null;
        const formData = new FormData();
        formData.append("file", input.files[0]);
        const result = await AuthGuard.apiCall("/blogs/upload-image", { method: "POST", body: formData });
        return result.path;
    }

    async function saveBlog(action) {
        msg.textContent = "";
        try {
            const featured_image = await uploadImageIfNeeded();
            const id = document.getElementById("blog-id").value;
            const payload = {
                title: document.getElementById("blog-title").value,
                content: document.getElementById("blog-content").value,
                category_id: document.getElementById("blog-form-category").value ? parseInt(document.getElementById("blog-form-category").value) : null,
                tags: document.getElementById("blog-tags").value,
                featured_image,
                action,
            };
            await AuthGuard.apiCall(id ? `/blogs/${id}` : "/blogs", { method: id ? "PUT" : "POST", body: JSON.stringify(payload) });
            modal.classList.remove("active");
            await Promise.all([loadBlogs(), loadAnalytics()]);
        } catch (err) {
            msg.textContent = err.message;
        }
    }

    async function deleteBlog(id) {
        if (!confirm("Delete this blog?")) return;
        await AuthGuard.apiCall(`/blogs/${id}`, { method: "DELETE" });
        await Promise.all([loadBlogs(), loadAnalytics()]);
    }

    document.getElementById("btn-new-blog").addEventListener("click", () => openModal());
    document.getElementById("btn-close-blog").addEventListener("click", () => modal.classList.remove("active"));
    document.getElementById("btn-save-draft").addEventListener("click", () => saveBlog("draft"));
    document.getElementById("btn-submit-review").addEventListener("click", () => saveBlog("submit"));
    document.getElementById("btn-publish-now").addEventListener("click", () => saveBlog("publish"));
    document.getElementById("blog-image").addEventListener("change", event => {
        const file = event.target.files[0];
        if (!file) return;
        const preview = document.getElementById("image-preview");
        preview.src = URL.createObjectURL(file);
        preview.classList.remove("hidden");
    });
    ["blog-search", "blog-status", "blog-category"].forEach(id => document.getElementById(id).addEventListener("input", loadBlogs));

    await loadCategories();
    await Promise.all([loadBlogs(), loadAnalytics()]);
});
