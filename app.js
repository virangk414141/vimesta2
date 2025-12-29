// Vimesta Cloud - Main Application JavaScript
// ==========================================

const App = {
    // API Configuration
    apiUrl: 'http://localhost:5000/api',
    
    // State
    user: null,
    token: null,
    
    // Initialize app
    init() {
        this.loadUserFromStorage();
        this.setupEventListeners();
    },
    
    // Load user from localStorage
    loadUserFromStorage() {
        this.token = localStorage.getItem('vimesta_token');
        const userStr = localStorage.getItem('vimesta_user');
        if (userStr) {
            this.user = JSON.parse(userStr);
        }
    },
    
    // Save user to localStorage
    saveUserToStorage(token, user) {
        this.token = token;
        this.user = user;
        localStorage.setItem('vimesta_token', token);
        localStorage.setItem('vimesta_user', JSON.stringify(user));
    },
    
    // Clear user from localStorage
    clearUserFromStorage() {
        this.token = null;
        this.user = null;
        localStorage.removeItem('vimesta_token');
        localStorage.removeItem('vimesta_user');
    },
    
    // Check if user is authenticated
    isAuthenticated() {
        return !!this.token && !!this.user;
    },
    
    // Setup global event listeners
    setupEventListeners() {
        // Handle ESC key to close modals
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                document.querySelectorAll('.modal.active').forEach(modal => {
                    modal.classList.remove('active');
                });
            }
        });
    },
    
    // API Request helper
    async request(endpoint, options = {}) {
        const url = `${this.apiUrl}${endpoint}`;
        const headers = {
            ...options.headers
        };
        
        // Add auth token if available
        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }
        
        // Add content type for JSON requests
        if (options.body && !(options.body instanceof FormData)) {
            headers['Content-Type'] = 'application/json';
            options.body = JSON.stringify(options.body);
        }
        
        try {
            const response = await fetch(url, {
                ...options,
                headers
            });
            
            const data = await response.json();
            
            // Handle auth errors
            if (response.status === 401) {
                this.clearUserFromStorage();
                if (window.location.pathname.includes('dashboard')) {
                    window.location.href = 'index.html';
                }
            }
            
            return data;
        } catch (error) {
            console.error('API Request Error:', error);
            throw error;
        }
    },
    
    // Auth methods
    async login(telegramId, userData = {}) {
        const data = await this.request('/auth/telegram', {
            method: 'POST',
            body: {
                id: telegramId,
                ...userData
            }
        });
        
        if (data.success) {
            this.saveUserToStorage(data.token, data.user);
        }
        
        return data;
    },
    
    logout() {
        this.clearUserFromStorage();
        window.location.href = 'index.html';
    },
    
    // File methods
    async getFiles(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        return await this.request(`/files/list?${queryString}`);
    },
    
    async uploadFile(file, folderId = null) {
        const formData = new FormData();
        formData.append('file', file);
        if (folderId) {
            formData.append('folder_id', folderId);
        }
        
        return await this.request('/files/upload', {
            method: 'POST',
            body: formData
        });
    },
    
    async downloadFile(fileId) {
        return await this.request(`/files/${fileId}/download`);
    },
    
    async deleteFile(fileId) {
        return await this.request(`/files/${fileId}`, {
            method: 'DELETE'
        });
    },
    
    async shareFile(fileId) {
        return await this.request(`/files/${fileId}/share`, {
            method: 'POST'
        });
    },
    
    // Folder methods
    async getFolders(parentId = null) {
        const params = parentId ? `?parent_id=${parentId}` : '';
        return await this.request(`/folders/list${params}`);
    },
    
    async createFolder(name, parentId = null) {
        return await this.request('/folders/create', {
            method: 'POST',
            body: { name, parent_id: parentId }
        });
    },
    
    async deleteFolder(folderId) {
        return await this.request(`/folders/${folderId}`, {
            method: 'DELETE'
        });
    },
    
    // User methods
    async getProfile() {
        return await this.request('/user/profile');
    },
    
    async getStorageStats() {
        return await this.request('/user/storage');
    }
};

// Utility functions
const Utils = {
    // Format file size
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },
    
    // Format date
    formatDate(dateStr, format = 'short') {
        const date = new Date(dateStr);
        
        if (format === 'short') {
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        } else if (format === 'full') {
            return date.toLocaleDateString('en-US', { 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        }
        
        return date.toLocaleString();
    },
    
    // Get file type from filename
    getFileType(filename) {
        const ext = filename.toLowerCase().split('.').pop();
        
        const types = {
            image: ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg'],
            video: ['mp4', 'avi', 'mkv', 'mov', 'webm', 'wmv'],
            audio: ['mp3', 'wav', 'ogg', 'flac', 'm4a', 'aac'],
            document: ['pdf', 'doc', 'docx', 'txt', 'xlsx', 'pptx', 'xls'],
            archive: ['zip', 'rar', '7z', 'tar', 'gz'],
            code: ['js', 'py', 'html', 'css', 'json', 'xml', 'java', 'cpp']
        };
        
        for (const [type, extensions] of Object.entries(types)) {
            if (extensions.includes(ext)) {
                return type;
            }
        }
        
        return 'other';
    },
    
    // Get file icon
    getFileIcon(type) {
        const icons = {
            image: '🖼️',
            video: '🎬',
            audio: '🎵',
            document: '📄',
            archive: '📦',
            code: '💻',
            other: '📎'
        };
        return icons[type] || icons['other'];
    },
    
    // Get file icon background color
    getFileIconBg(type) {
        const colors = {
            image: 'rgba(59, 130, 246, 0.2)',
            video: 'rgba(239, 68, 68, 0.2)',
            audio: 'rgba(168, 85, 247, 0.2)',
            document: 'rgba(34, 197, 94, 0.2)',
            archive: 'rgba(245, 158, 11, 0.2)',
            code: 'rgba(6, 182, 212, 0.2)',
            other: 'rgba(156, 163, 175, 0.2)'
        };
        return colors[type] || colors['other'];
    },
    
    // Get file icon color
    getFileIconColor(type) {
        const colors = {
            image: '#3b82f6',
            video: '#ef4444',
            audio: '#a855f7',
            document: '#22c55e',
            archive: '#f59e0b',
            code: '#06b6d4',
            other: '#9ca3af'
        };
        return colors[type] || colors['other'];
    },
    
    // Show toast notification
    showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        if (!container) return;
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `<span>${message}</span>`;
        container.appendChild(toast);
        
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    },
    
    // Debounce function
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    // Copy to clipboard
    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch (err) {
            console.error('Failed to copy:', err);
            return false;
        }
    }
};

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    App.init();
});

// Export for use in other scripts
window.App = App;
window.Utils = Utils;
