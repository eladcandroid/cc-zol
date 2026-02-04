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
        .btn-delete { background: #7f1d1d; color: #fff; }
        .btn-delete:hover { background: #991b1b; }

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
                <button class="btn btn-refresh" onclick="refresh()">Refresh</button>
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
