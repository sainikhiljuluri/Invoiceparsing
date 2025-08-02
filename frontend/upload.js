// Simple and reliable multi-option upload functionality
console.log('🚀 Upload.js loaded');

// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('📋 DOM ready, initializing upload...');
    
    // Get DOM elements
    const cameraOption = document.getElementById('cameraOption');
    const galleryOption = document.getElementById('galleryOption');
    const pdfOption = document.getElementById('pdfOption');
    const cameraInput = document.getElementById('cameraInput');
    const galleryInput = document.getElementById('galleryInput');
    const pdfInput = document.getElementById('pdfInput');
    const previewArea = document.getElementById('previewArea');
    const filePreview = document.getElementById('filePreview');
    const fileInfo = document.getElementById('fileInfo');
    const clearSelection = document.getElementById('clearSelection');
    const uploadStatus = document.getElementById('uploadStatus');
    const submitBtn = document.getElementById('submitBtn');
    
    let selectedFile = null;
    let uploadMethod = null;
    
    console.log('🔍 Elements found:', {
        cameraOption: !!cameraOption,
        galleryOption: !!galleryOption,
        pdfOption: !!pdfOption,
        cameraInput: !!cameraInput,
        galleryInput: !!galleryInput,
        pdfInput: !!pdfInput,
        submitBtn: !!submitBtn
    });
    
    // Camera option click
    if (cameraOption && cameraInput) {
        cameraOption.onclick = function() {
            console.log('📷 Camera clicked');
            cameraInput.click();
        };
        
        cameraInput.onchange = function(e) {
            console.log('📷 Camera file selected');
            handleFileSelection(e.target.files[0], 'camera');
        };
    }
    
    // Gallery option click
    if (galleryOption && galleryInput) {
        galleryOption.onclick = function() {
            console.log('🖼️ Gallery clicked');
            galleryInput.click();
        };
        
        galleryInput.onchange = function(e) {
            console.log('🖼️ Gallery file selected');
            handleFileSelection(e.target.files[0], 'gallery');
        };
    }
    
    // PDF option click
    if (pdfOption && pdfInput) {
        pdfOption.onclick = function() {
            console.log('📄 PDF clicked');
            pdfInput.click();
        };
        
        pdfInput.onchange = function(e) {
            console.log('📄 PDF file selected');
            handleFileSelection(e.target.files[0], 'pdf');
        };
    }
    
    // Clear selection
    if (clearSelection) {
        clearSelection.onclick = function() {
            console.log('🗑️ Clear clicked');
            clearFileSelection();
        };
    }
    
    // Submit button
    if (submitBtn) {
        submitBtn.onclick = function() {
            console.log('🚀 Submit clicked');
            if (selectedFile) {
                uploadFile(selectedFile);
            } else {
                showError('Please select a file first');
            }
        };
    }
    
    // Handle file selection
    function handleFileSelection(file, method) {
        if (!file) return;
        
        console.log('📁 File selected:', file.name, 'Method:', method);
        
        uploadMethod = method;
        
        if (validateFile(file, method)) {
            selectedFile = file;
            showFilePreview(file, method);
            if (submitBtn) {
                submitBtn.disabled = false;
            }
        }
    }
    
    // Validate file
    function validateFile(file, method) {
        const maxSize = 10 * 1024 * 1024; // 10MB
        
        if (method === 'pdf') {
            if (file.type !== 'application/pdf') {
                showError('Please select a PDF file.');
                return false;
            }
        } else {
            if (!file.type.startsWith('image/')) {
                showError('Please select an image file.');
                return false;
            }
        }
        
        if (file.size > maxSize) {
            showError('File size must be less than 10MB.');
            return false;
        }
        
        return true;
    }
    
    // Show file preview
    function showFilePreview(file, method) {
        const methodIcons = {
            camera: 'fas fa-camera text-blue-600',
            gallery: 'fas fa-images text-green-600',
            pdf: 'fas fa-file-pdf text-purple-600'
        };
        
        const methodLabels = {
            camera: 'Camera Capture',
            gallery: 'Gallery Selection',
            pdf: 'PDF Upload'
        };
        
        // Show preview area
        if (previewArea) {
            previewArea.classList.remove('hidden');
        }
        
        // Create preview content
        if (filePreview) {
            if (method === 'pdf') {
                filePreview.innerHTML = `
                    <div class="flex items-center justify-center p-8">
                        <i class="fas fa-file-pdf text-6xl text-purple-600 mb-4"></i>
                    </div>
                    <p class="font-semibold text-gray-800">${file.name}</p>
                `;
            } else {
                // Create image preview
                const reader = new FileReader();
                reader.onload = function(e) {
                    filePreview.innerHTML = `
                        <img src="${e.target.result}" alt="Preview" class="max-w-full max-h-64 mx-auto rounded-lg shadow-md">
                        <p class="font-semibold text-gray-800 mt-3">${file.name}</p>
                    `;
                };
                reader.readAsDataURL(file);
            }
        }
        
        // Show file info
        if (fileInfo) {
            fileInfo.innerHTML = `
                <div class="flex items-center justify-between">
                    <div class="flex items-center">
                        <i class="${methodIcons[method]} mr-2"></i>
                        <span class="font-medium">${methodLabels[method]}</span>
                    </div>
                    <div class="text-right">
                        <span class="text-sm">${(file.size / 1024 / 1024).toFixed(2)} MB</span>
                    </div>
                </div>
            `;
        }
        
        showSuccess(`File selected via ${methodLabels[method].toLowerCase()}`);
    }
    
    // Clear file selection
    function clearFileSelection() {
        selectedFile = null;
        uploadMethod = null;
        
        if (previewArea) previewArea.classList.add('hidden');
        if (filePreview) filePreview.innerHTML = '';
        if (fileInfo) fileInfo.innerHTML = '';
        if (submitBtn) submitBtn.disabled = true;
        
        // Reset all file inputs
        if (cameraInput) cameraInput.value = '';
        if (galleryInput) galleryInput.value = '';
        if (pdfInput) pdfInput.value = '';
        
        clearStatus();
    }
    
    // Upload file
    async function uploadFile(file) {
        if (!file) {
            showError('Please select a file first');
            return;
        }
        
        console.log('📤 Uploading file:', file.name);
        
        const formData = new FormData();
        formData.append('file', file);
        
        // Disable submit button and show processing
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Processing...';
        }
        
        showStatus('Uploading and processing invoice...', 'info');
        
        try {
            const response = await fetch('http://localhost:8001/api/v1/invoices/upload', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            console.log('✅ Upload successful:', result);
            
            showSuccess(`Invoice uploaded successfully! ID: ${result.invoice_id || 'Generated'}`);
            
            // Reset form after 3 seconds
            setTimeout(() => {
                clearFileSelection();
            }, 3000);
            
        } catch (error) {
            console.error('❌ Upload error:', error);
            showError('Upload failed: ' + error.message);
            
            // Re-enable submit button
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fas fa-paper-plane mr-2"></i>Process Invoice';
            }
        }
    }
    
    // Utility functions
    function showStatus(message, type = 'info') {
        if (!uploadStatus) return;
        
        const colors = {
            info: 'bg-blue-50 border-blue-200 text-blue-800',
            success: 'bg-green-50 border-green-200 text-green-800',
            error: 'bg-red-50 border-red-200 text-red-800'
        };
        
        const icons = {
            info: 'fas fa-info-circle',
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-circle'
        };
        
        uploadStatus.innerHTML = `
            <div class="${colors[type]} border rounded-lg p-4">
                <div class="flex items-center">
                    <i class="${icons[type]} mr-2"></i>
                    <span class="font-medium">${message}</span>
                </div>
            </div>
        `;
    }
    
    function showSuccess(message) {
        showStatus(message, 'success');
    }
    
    function showError(message) {
        showStatus(message, 'error');
        
        // Auto-hide error after 5 seconds
        setTimeout(() => {
            clearStatus();
        }, 5000);
    }
    
    function clearStatus() {
        if (uploadStatus) {
            uploadStatus.innerHTML = '';
        }
    }
    
    console.log('✅ Upload functionality initialized successfully!');
});
