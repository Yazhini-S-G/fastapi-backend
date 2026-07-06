# ----- Default App Setup -----
LOG_PATH = "data/logs"
DEFAULT_FRONTEND_URL = "http://localhost:3000"
UTF_8_ENCODING = "utf-8"
CASCADE_ON_DELETE = "CASCADE"
USER_ID_FOREIGN_KEY = "user.id"

# Auth constants
AUTHENTICATE_HEADER_NAME = "WWW-Authenticate"
BEARER_SCHEME = "Bearer"
AUTHENTICATE_BEARER_HEADER = {AUTHENTICATE_HEADER_NAME: BEARER_SCHEME}

# Role constants
ROLE_SUPER_ADMIN = "Super Admin"
ROLE_ADMIN = "Admin"
ROLE_USER = "User"

# Shared response details
ACCESS_DENIED_DETAIL = "Access Denied"
EMAIL_ALREADY_EXISTS_DETAIL = "Email already exists"
PASSWORDS_DO_NOT_MATCH_DETAIL = "Passwords do not match"

# Blog status constants
BLOG_STATUS_DRAFT = "Draft"
BLOG_STATUS_PENDING_REVIEW = "Pending Review"
BLOG_STATUS_APPROVED = "Approved"
BLOG_STATUS_PUBLISHED = "Published"
BLOG_STATUS_REJECTED = "Rejected"

# Blog permission constants
PERM_CREATE_BLOG = "create_blog"
PERM_VIEW_BLOG = "view_blog"
PERM_EDIT_BLOG = "edit_blog"
PERM_EDIT_OWN_BLOG = "edit_own_blog"
PERM_DELETE_BLOG = "delete_blog"
PERM_REVIEW_BLOG = "review_blog"
PERM_PUBLISH_BLOG = "publish_blog"
PERM_FEATURE_BLOG = "feature_blog"
PERM_MANAGE_BLOG_CATEGORIES = "manage_blog_categories"
PERM_SAVE_DRAFT = "save_draft"
PERM_SUBMIT_FOR_REVIEW = "submit_for_review"
PERM_UPLOAD_BLOG_IMAGE = "upload_blog_image"
PERM_VIEW_BLOG_ANALYTICS = "view_blog_analytics"
PERM_VIEW_REPORTS = "view_reports"
PERM_MANAGE_ROLES = "manage_roles"

# Audit modules
MODULE_AUTH = "Auth"
MODULE_BLOG_MANAGEMENT = "Blog Management"
MODULE_ROLE_MANAGEMENT = "Role Management"
MODULE_USER_MANAGEMENT = "User Management"

# Audit actions
ACTION_LOGIN = "Login"
ACTION_LOGOUT = "Logout"
ACTION_FAILED_LOGIN = "Failed Login"
ACTION_CREATE_BLOG = "Create Blog"
ACTION_UPDATE_BLOG = "Update Blog"
ACTION_DELETE_BLOG = "Delete Blog"
ACTION_APPROVE_BLOG = "Approve Blog"
ACTION_PUBLISH_BLOG = "Publish Blog"
ACTION_SUBMIT_BLOG_FOR_REVIEW = "Submit Blog For Review"
