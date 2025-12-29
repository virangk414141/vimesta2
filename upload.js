// Vimesta Cloud - File Upload Handler
// ====================================

const FileUploader = {
    // Configuration
    maxFileSize: 2 * 1024 * 1024 * 1024, // 2GB
    allowedTypes: null, // null means allow all

    // State
    uploadQueue: [],
    isUploading: false,
    currentUpload: null,

    // Initialize uploader
    init(options = {}) {
        this.maxFileSize = options.maxFileSize || this.maxFileSize;
        this.allowedTypes = options.allowedTypes || null;
        this.onProgress = options.onProgress || (() => { });
        this.onComplete = options.onComplete || (() => { });
        this.onError = options.onError || (() => { });

        return this;
    },

    // Validate file
    validateFile(file) {
        // Check file size
        if (file.size > this.maxFileSize) {
            return {
                valid: false,
                error: `File size exceeds maximum limit of ${Utils.formatFileSize(this.maxFileSize)}`
            };
        }

        // Check file type if restrictions exist
        if (this.allowedTypes && this.allowedTypes.length > 0) {
            const ext = file.name.split('.').pop().toLowerCase();
            if (!this.allowedTypes.includes(ext)) {
                return {
                    valid: false,
                    error: `File type .${ext} is not allowed`
                };
            }
        }

        return { valid: true };
    },

    // Add files to queue
    addFiles(fileList, folderId = null) {
        const files = Array.from(fileList);
        const results = [];

        files.forEach(file => {
            const validation = this.validateFile(file);

            if (validation.valid) {
                this.uploadQueue.push({
                    file,
                    folderId,
                    progress: 0,
                    status: 'pending' // pending, uploading, completed, error
                });
                results.push({ file: file.name, success: true });
            } else {
                results.push({ file: file.name, success: false, error: validation.error });
                this.onError(file, validation.error);
            }
        });

        // Start processing queue
        this.processQueue();

        return results;
    },

    // Process upload queue
    async processQueue() {
        if (this.isUploading || this.uploadQueue.length === 0) {
            return;
        }

        this.isUploading = true;

        while (this.uploadQueue.length > 0) {
            const item = this.uploadQueue[0];
            item.status = 'uploading';
            this.currentUpload = item;

            try {
                await this.uploadFile(item);
                item.status = 'completed';
                this.onComplete(item.file);
            } catch (error) {
                item.status = 'error';
                item.error = error.message;
                this.onError(item.file, error.message);
            }

            // Remove from queue
            this.uploadQueue.shift();
        }

        this.isUploading = false;
        this.currentUpload = null;
    },

    // Upload single file
    async uploadFile(item) {
        const { file, folderId } = item;

        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            const formData = new FormData();

            formData.append('file', file);
            if (folderId) {
                formData.append('folder_id', folderId);
            }

            // Progress handler
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const progress = Math.round((e.loaded / e.total) * 100);
                    item.progress = progress;
                    this.onProgress(file, progress);
                }
            });

            // Load handler
            xhr.addEventListener('load', () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        if (response.success) {
                            resolve(response);
                        } else {
                            reject(new Error(response.error || 'Upload failed'));
                        }
                    } catch (e) {
                        reject(new Error('Invalid response from server'));
                    }
                } else {
                    reject(new Error(`Upload failed with status ${xhr.status}`));
                }
            });

            // Error handler
            xhr.addEventListener('error', () => {
                reject(new Error('Network error during upload'));
            });

            // Abort handler
            xhr.addEventListener('abort', () => {
                reject(new Error('Upload cancelled'));
            });

            // Open and send
            xhr.open('POST', `${App.apiUrl}/files/upload`);
            xhr.setRequestHeader('Authorization', `Bearer ${App.token}`);
            xhr.send(formData);

            // Store xhr for potential cancellation
            item.xhr = xhr;
        });
    },

    // Cancel current upload
    cancelCurrent() {
        if (this.currentUpload && this.currentUpload.xhr) {
            this.currentUpload.xhr.abort();
        }
    },

    // Cancel all uploads
    cancelAll() {
        this.cancelCurrent();
        this.uploadQueue = [];
    },

    // Get queue status
    getStatus() {
        return {
            isUploading: this.isUploading,
            queueLength: this.uploadQueue.length,
            currentFile: this.currentUpload ? this.currentUpload.file.name : null,
            currentProgress: this.currentUpload ? this.currentUpload.progress : 0
        };
    }
};

// Drag and Drop Handler
const DragDropHandler = {
    // Initialize drag and drop on an element
    init(element, options = {}) {
        if (!element) return;

        const onDrop = options.onDrop || (() => { });
        const onDragOver = options.onDragOver || (() => { });
        const onDragLeave = options.onDragLeave || (() => { });

        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            element.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });

        // Drag enter/over
        ['dragenter', 'dragover'].forEach(eventName => {
            element.addEventListener(eventName, () => {
                element.classList.add('dragover');
                onDragOver();
            });
        });

        // Drag leave
        element.addEventListener('dragleave', (e) => {
            // Only trigger if actually leaving the element
            if (!element.contains(e.relatedTarget)) {
                element.classList.remove('dragover');
                onDragLeave();
            }
        });

        // Drop
        element.addEventListener('drop', (e) => {
            element.classList.remove('dragover');

            const files = e.dataTransfer.files;
            if (files.length > 0) {
                onDrop(files);
            }
        });

        return this;
    }
};

// Chunk uploader for large files (optional, for future use)
const ChunkUploader = {
    chunkSize: 10 * 1024 * 1024, // 10MB chunks

    async uploadInChunks(file, folderId = null, onProgress = () => { }) {
        const totalChunks = Math.ceil(file.size / this.chunkSize);
        let uploadedChunks = 0;

        for (let i = 0; i < totalChunks; i++) {
            const start = i * this.chunkSize;
            const end = Math.min(start + this.chunkSize, file.size);
            const chunk = file.slice(start, end);

            const formData = new FormData();
            formData.append('chunk', chunk);
            formData.append('filename', file.name);
            formData.append('chunk_index', i);
            formData.append('total_chunks', totalChunks);
            if (folderId) {
                formData.append('folder_id', folderId);
            }

            try {
                const response = await fetch(`${App.apiUrl}/files/upload-chunk`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${App.token}`
                    },
                    body: formData
                });

                if (!response.ok) {
                    throw new Error(`Chunk ${i + 1} upload failed`);
                }

                uploadedChunks++;
                const progress = Math.round((uploadedChunks / totalChunks) * 100);
                onProgress(progress);

            } catch (error) {
                throw new Error(`Failed to upload chunk ${i + 1}: ${error.message}`);
            }
        }

        return { success: true, message: 'File uploaded successfully' };
    }
};

// Export
window.FileUploader = FileUploader;
window.DragDropHandler = DragDropHandler;
window.ChunkUploader = ChunkUploader;
