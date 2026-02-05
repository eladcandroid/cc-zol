"""Admin API routes for user management."""

import os
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/admin", tags=["admin"])

# Simple admin password from environment
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")


class AdminAuth(BaseModel):
    password: str


class UserUpdate(BaseModel):
    active: Optional[bool] = None
    verified: Optional[bool] = None
    intercept_token: Optional[str] = None


class UserCreate(BaseModel):
    email: str
    intercept_token: str
    active: bool = False


def verify_admin(request: Request):
    """Simple admin auth via header."""
    auth = request.headers.get("X-Admin-Password")
    if auth != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid admin password")
    return True


@router.get("/", response_class=HTMLResponse)
async def admin_ui():
    """Serve admin UI."""
    html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>cc-zol Admin</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0a0a;
            color: #e5e5e5;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { margin-bottom: 20px; color: #fff; }

        /* Login */
        #login-form {
            max-width: 300px;
            margin: 100px auto;
            padding: 30px;
            background: #1a1a1a;
            border-radius: 8px;
        }
        #login-form input {
            width: 100%;
            padding: 10px;
            margin-bottom: 15px;
            border: 1px solid #333;
            border-radius: 4px;
            background: #0a0a0a;
            color: #fff;
        }
        #login-form button {
            width: 100%;
            padding: 10px;
            background: #3b82f6;
            border: none;
            border-radius: 4px;
            color: #fff;
            cursor: pointer;
        }
        #login-form button:hover { background: #2563eb; }

        /* Stats */
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: #1a1a1a;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }
        .stat-value {
            font-size: 2em;
            font-weight: bold;
            color: #3b82f6;
        }
        .stat-label {
            font-size: 0.9em;
            color: #888;
            margin-top: 5px;
        }

        /* Table */
        table {
            width: 100%;
            border-collapse: collapse;
            background: #1a1a1a;
            border-radius: 8px;
            overflow: hidden;
        }
        th, td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #333;
        }
        th { background: #252525; color: #fff; }
        tr:hover { background: #252525; }

        /* Badges */
        .badge {
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
        }
        .badge-green { background: #166534; color: #4ade80; }
        .badge-red { background: #7f1d1d; color: #f87171; }
        .badge-gray { background: #374151; color: #9ca3af; }

        /* Buttons */
        .btn {
            padding: 6px 12px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.85em;
        }
        .btn-toggle { background: #374151; color: #fff; }
        .btn-toggle:hover { background: #4b5563; }
        .btn-edit { background: #1e40af; color: #fff; }
        .btn-edit:hover { background: #1d4ed8; }
        .btn-delete { background: #7f1d1d; color: #fff; }
        .btn-delete:hover { background: #991b1b; }

        /* Modal */
        .modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
        }
        .modal-content {
            background: #1a1a1a;
            padding: 30px;
            border-radius: 8px;
            width: 100%;
            max-width: 500px;
        }
        .modal-content h3 {
            margin-bottom: 20px;
            color: #fff;
        }
        .modal-content label {
            display: block;
            margin-bottom: 5px;
            color: #888;
            font-size: 0.9em;
        }
        .modal-content input {
            width: 100%;
            padding: 10px;
            margin-bottom: 15px;
            border: 1px solid #333;
            border-radius: 4px;
            background: #0a0a0a;
            color: #fff;
            font-family: monospace;
        }
        .modal-content input:read-only {
            background: #252525;
            color: #888;
        }
        .modal-buttons {
            display: flex;
            gap: 10px;
            justify-content: flex-end;
            margin-top: 20px;
        }
        .modal-buttons .btn {
            padding: 10px 20px;
        }
        .btn-cancel { background: #374151; color: #fff; }
        .btn-cancel:hover { background: #4b5563; }
        .btn-save { background: #166534; color: #fff; }
        .btn-save:hover { background: #15803d; }
        .btn-generate { background: #6b21a8; color: #fff; font-size: 0.8em; padding: 6px 10px; }
        .btn-generate:hover { background: #7c3aed; }
        .btn-copy { background: #0369a1; color: #fff; font-size: 0.8em; padding: 6px 10px; }
        .btn-copy:hover { background: #0284c7; }
        .input-group {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        .input-group input { flex: 1; margin-bottom: 0; }

        /* Hidden */
        .hidden { display: none; }

        /* Refresh */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        .btn-refresh {
            background: #1f2937;
            color: #fff;
            padding: 8px 16px;
        }
        .btn-refresh:hover { background: #374151; }
        .btn-add {
            background: #166534;
            color: #fff;
            padding: 8px 16px;
            margin-right: 10px;
        }
        .btn-add:hover { background: #15803d; }
        .header-buttons {
            display: flex;
            gap: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Login Form -->
        <div id="login-form">
            <h2 style="margin-bottom: 20px; text-align: center;">Admin Login</h2>
            <input type="password" id="password" placeholder="Admin Password">
            <button onclick="login()">Login</button>
            <p id="login-error" style="color: #f87171; margin-top: 10px; text-align: center;"></p>
        </div>

        <!-- Dashboard -->
        <div id="dashboard" class="hidden">
            <div class="header">
                <h1>cc-zol Admin</h1>
                <div class="header-buttons">
                    <button class="btn btn-add" onclick="openAddModal()">+ Add User</button>
                    <button class="btn btn-refresh" onclick="refresh()">Refresh</button>
                </div>
            </div>

            <!-- Stats -->
            <div class="stats" id="stats"></div>

            <!-- Users Table -->
            <h2 style="margin-bottom: 15px;">Users</h2>
            <table>
                <thead>
                    <tr>
                        <th>Email</th>
                        <th>Status</th>
                        <th>Verified</th>
                        <th>Token</th>
                        <th>Last Login</th>
                        <th>Created</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="users-table"></tbody>
            </table>
        </div>

        <!-- Edit User Modal -->
        <div id="edit-modal" class="modal hidden">
            <div class="modal-content">
                <h3>Edit User</h3>
                <label>Email</label>
                <input type="text" id="edit-email" readonly>
                <label>Token</label>
                <div class="input-group">
                    <input type="text" id="edit-token" placeholder="Enter token or generate new">
                    <button class="btn btn-copy" onclick="copyToken('edit-token')">Copy</button>
                    <button class="btn btn-generate" onclick="generateToken('edit-token')">Generate</button>
                </div>
                <div class="modal-buttons">
                    <button class="btn btn-cancel" onclick="closeEditModal()">Cancel</button>
                    <button class="btn btn-save" onclick="saveUser()">Save</button>
                </div>
            </div>
        </div>

        <!-- Add User Modal -->
        <div id="add-modal" class="modal hidden">
            <div class="modal-content">
                <h3>Add Pre-configured User</h3>
                <label>Email</label>
                <input type="email" id="add-email" placeholder="user@example.com">
                <label>Token</label>
                <div class="input-group">
                    <input type="text" id="add-token" placeholder="Enter token or generate new">
                    <button class="btn btn-copy" onclick="copyToken('add-token')">Copy</button>
                    <button class="btn btn-generate" onclick="generateToken('add-token')">Generate</button>
                </div>
                <label style="display: flex; align-items: center; gap: 8px; margin-top: 10px;">
                    <input type="checkbox" id="add-active">
                    <span>Active (user can login immediately after verification)</span>
                </label>
                <p style="color: #888; font-size: 0.85em; margin-top: 15px;">
                    User will need to verify email before using the CLI.
                    Their pre-configured token will be preserved.
                </p>
                <div class="modal-buttons">
                    <button class="btn btn-cancel" onclick="closeAddModal()">Cancel</button>
                    <button class="btn btn-save" onclick="createUser()">Create User</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        let adminPassword = '';

        function login() {
            adminPassword = document.getElementById('password').value;
            fetch('/admin/api/stats', {
                headers: { 'X-Admin-Password': adminPassword }
            })
            .then(r => {
                if (r.ok) {
                    document.getElementById('login-form').classList.add('hidden');
                    document.getElementById('dashboard').classList.remove('hidden');
                    refresh();
                } else {
                    document.getElementById('login-error').textContent = 'Invalid password';
                }
            });
        }

        function refresh() {
            loadStats();
            loadUsers();
        }

        function loadStats() {
            fetch('/admin/api/stats', {
                headers: { 'X-Admin-Password': adminPassword }
            })
            .then(r => r.json())
            .then(stats => {
                document.getElementById('stats').innerHTML = `
                    <div class="stat-card">
                        <div class="stat-value">${stats.total_users}</div>
                        <div class="stat-label">Total Users</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${stats.active_users}</div>
                        <div class="stat-label">Active</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${stats.inactive_users}</div>
                        <div class="stat-label">Inactive</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${stats.verified_users}</div>
                        <div class="stat-label">Verified</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${stats.logins_last_24h}</div>
                        <div class="stat-label">Logins (24h)</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${stats.signups_last_7d}</div>
                        <div class="stat-label">Signups (7d)</div>
                    </div>
                `;
            });
        }

        function loadUsers() {
            fetch('/admin/api/users', {
                headers: { 'X-Admin-Password': adminPassword }
            })
            .then(r => r.json())
            .then(users => {
                document.getElementById('users-table').innerHTML = users.map(u => `
                    <tr>
                        <td>${u.email}</td>
                        <td>
                            <span class="badge ${u.active !== false ? 'badge-green' : 'badge-red'}">
                                ${u.active !== false ? 'Active' : 'Inactive'}
                            </span>
                        </td>
                        <td>
                            <span class="badge ${u.verified ? 'badge-green' : 'badge-gray'}">
                                ${u.verified ? 'Yes' : 'No'}
                            </span>
                        </td>
                        <td>${u.has_token ? u.intercept_token : '-'}</td>
                        <td>${u.last_logged_in ? new Date(u.last_logged_in).toLocaleString() : '-'}</td>
                        <td>${new Date(u.created_at).toLocaleDateString()}</td>
                        <td>
                            <button class="btn btn-edit" onclick="editUser('${u.email}')">Edit</button>
                            <button class="btn btn-toggle" onclick="toggleActive('${u.email}')">
                                ${u.active !== false ? 'Disable' : 'Enable'}
                            </button>
                            <button class="btn btn-delete" onclick="deleteUser('${u.email}')">Delete</button>
                        </td>
                    </tr>
                `).join('');
            });
        }

        function toggleActive(email) {
            fetch(`/admin/api/users/${encodeURIComponent(email)}/toggle`, {
                method: 'POST',
                headers: { 'X-Admin-Password': adminPassword }
            })
            .then(() => refresh());
        }

        function deleteUser(email) {
            if (confirm(`Delete user ${email}?`)) {
                fetch(`/admin/api/users/${encodeURIComponent(email)}`, {
                    method: 'DELETE',
                    headers: { 'X-Admin-Password': adminPassword }
                })
                .then(() => refresh());
            }
        }

        function editUser(email) {
            document.getElementById('edit-email').value = email;
            document.getElementById('edit-token').value = 'Loading...';
            document.getElementById('edit-modal').classList.remove('hidden');

            // Fetch full user details including full token
            fetch(`/admin/api/users/${encodeURIComponent(email)}`, {
                headers: { 'X-Admin-Password': adminPassword }
            })
            .then(r => r.json())
            .then(user => {
                document.getElementById('edit-token').value = user.intercept_token || '';
            })
            .catch(() => {
                document.getElementById('edit-token').value = '';
            });
        }

        function closeEditModal() {
            document.getElementById('edit-modal').classList.add('hidden');
        }

        function generateToken(targetId) {
            // Generate 64-char hex token
            const array = new Uint8Array(32);
            crypto.getRandomValues(array);
            const token = Array.from(array, b => b.toString(16).padStart(2, '0')).join('');
            document.getElementById(targetId).value = token;
        }

        function copyToken(targetId) {
            const input = document.getElementById(targetId);
            const token = input.value;
            if (!token || token === 'Loading...') return;

            navigator.clipboard.writeText(token).then(() => {
                // Brief visual feedback
                const btn = event.target;
                const originalText = btn.textContent;
                btn.textContent = 'Copied!';
                setTimeout(() => btn.textContent = originalText, 1500);
            });
        }

        function saveUser() {
            const email = document.getElementById('edit-email').value;
            const token = document.getElementById('edit-token').value.trim();

            if (!token) {
                alert('Please enter or generate a token');
                return;
            }

            fetch(`/admin/api/users/${encodeURIComponent(email)}`, {
                method: 'PATCH',
                headers: {
                    'X-Admin-Password': adminPassword,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ intercept_token: token })
            })
            .then(r => {
                if (r.ok) {
                    closeEditModal();
                    refresh();
                } else {
                    r.json().then(data => alert(data.detail || 'Error updating user'));
                }
            });
        }

        // Add User Modal functions
        function openAddModal() {
            document.getElementById('add-email').value = '';
            document.getElementById('add-token').value = '';
            document.getElementById('add-active').checked = false;
            document.getElementById('add-modal').classList.remove('hidden');
        }

        function closeAddModal() {
            document.getElementById('add-modal').classList.add('hidden');
        }

        function createUser() {
            const email = document.getElementById('add-email').value.trim();
            const token = document.getElementById('add-token').value.trim();
            const active = document.getElementById('add-active').checked;

            if (!email) {
                alert('Please enter an email');
                return;
            }
            if (!token) {
                alert('Please enter or generate a token');
                return;
            }

            fetch('/admin/api/users', {
                method: 'POST',
                headers: {
                    'X-Admin-Password': adminPassword,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ email, intercept_token: token, active })
            })
            .then(r => {
                if (r.ok) {
                    closeAddModal();
                    refresh();
                } else {
                    r.json().then(data => alert(data.detail || 'Error creating user'));
                }
            });
        }

        // Close modal on click outside
        document.getElementById('edit-modal').addEventListener('click', e => {
            if (e.target.id === 'edit-modal') closeEditModal();
        });
        document.getElementById('add-modal').addEventListener('click', e => {
            if (e.target.id === 'add-modal') closeAddModal();
        });

        // Enter key to login
        document.getElementById('password').addEventListener('keypress', e => {
            if (e.key === 'Enter') login();
        });
    </script>
</body>
</html>
    """
    return html


@router.get("/api/stats")
async def get_stats(request: Request, _: bool = Depends(verify_admin)):
    """Get user statistics."""
    user_db = request.app.state.user_db
    if not user_db:
        raise HTTPException(status_code=503, detail="Database not available")
    return await user_db.get_stats()


@router.get("/api/users")
async def list_users(request: Request, _: bool = Depends(verify_admin)):
    """List all users."""
    user_db = request.app.state.user_db
    if not user_db:
        raise HTTPException(status_code=503, detail="Database not available")
    return await user_db.list_users()


@router.get("/api/users/{email}")
async def get_user(email: str, request: Request, _: bool = Depends(verify_admin)):
    """Get full user details including full token (for edit modal)."""
    user_db = request.app.state.user_db
    if not user_db:
        raise HTTPException(status_code=503, detail="Database not available")

    user = await user_db.get_user_for_admin(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/api/users/{email}/toggle")
async def toggle_user(email: str, request: Request, _: bool = Depends(verify_admin)):
    """Toggle user active status."""
    user_db = request.app.state.user_db
    if not user_db:
        raise HTTPException(status_code=503, detail="Database not available")

    new_status = await user_db.toggle_user_active(email)
    if new_status is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {"email": email, "active": new_status}


@router.patch("/api/users/{email}")
async def update_user(email: str, updates: UserUpdate, request: Request, _: bool = Depends(verify_admin)):
    """Update user fields."""
    user_db = request.app.state.user_db
    if not user_db:
        raise HTTPException(status_code=503, detail="Database not available")

    update_dict = updates.model_dump(exclude_none=True)
    if not update_dict:
        raise HTTPException(status_code=400, detail="No valid updates provided")

    success = await user_db.update_user(email, update_dict)
    if not success:
        raise HTTPException(status_code=404, detail="User not found or no changes made")
    return {"email": email, "updated": True}


@router.delete("/api/users/{email}")
async def delete_user(email: str, request: Request, _: bool = Depends(verify_admin)):
    """Delete a user."""
    user_db = request.app.state.user_db
    if not user_db:
        raise HTTPException(status_code=503, detail="Database not available")

    success = await user_db.delete_user(email)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"email": email, "deleted": True}


@router.post("/api/users")
async def create_user(user_data: UserCreate, request: Request, _: bool = Depends(verify_admin)):
    """Create a pre-configured user with a pre-set token."""
    user_db = request.app.state.user_db
    if not user_db:
        raise HTTPException(status_code=503, detail="Database not available")

    result = await user_db.create_preconfigured_user(
        email=user_data.email,
        token=user_data.intercept_token,
        active=user_data.active,
    )

    if not result["created"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return {"email": user_data.email, "created": True}
