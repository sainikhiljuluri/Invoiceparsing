// API base URL
const API_URL = 'http://localhost:8001/api/v1';

// Test API connection on page load
document.addEventListener('DOMContentLoaded', async () => {
    console.log('🚀 DOM Content Loaded - Starting initialization...');
    
    try {
        const response = await fetch('http://localhost:8001/health');
        if (response.ok) {
            console.log('✅ Backend API is accessible');
        } else {
            console.warn('⚠️ Backend API responded with error:', response.status);
        }
    } catch (error) {
        console.error('❌ Backend API is not accessible:', error);
        // Don't show error immediately, let user try upload first
    }
    
    // Wait a bit for DOM to fully load
    setTimeout(() => {
        console.log('⏰ Initializing upload interface after timeout...');
        initializeUploadInterface();
    }, 100);
});

// DOM elements for multi-option upload
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

// Store selected file and upload method
let selectedFile = null;
let uploadMethod = null;

// Initialize multi-option upload interface
function initializeUploadInterface() {
    console.log('🔧 Initializing upload interface...');
    
    // Check if all DOM elements exist
    if (!cameraOption || !galleryOption || !pdfOption) {
        console.error('❌ Upload option elements not found!');
        return;
    }
    
    if (!cameraInput || !galleryInput || !pdfInput) {
        console.error('❌ File input elements not found!');
        return;
    }
    
    console.log('✅ All DOM elements found, setting up event listeners...');
    
    // Camera option click handler
    cameraOption.addEventListener('click', () => {
        console.log('📷 Camera option clicked');
        cameraInput.click();
    });
    
    // Gallery option click handler
    galleryOption.addEventListener('click', () => {
        console.log('🖼️ Gallery option clicked');
        galleryInput.click();
    });
    
    // PDF option click handler
    pdfOption.addEventListener('click', () => {
        console.log('📄 PDF option clicked');
        pdfInput.click();
    });
    
    // File input handlers
    cameraInput.addEventListener('change', (e) => {
        console.log('📷 Camera file selected:', e.target.files[0]?.name);
        handleFileSelection(e, 'camera');
    });
    
    galleryInput.addEventListener('change', (e) => {
        console.log('🖼️ Gallery file selected:', e.target.files[0]?.name);
        handleFileSelection(e, 'gallery');
    });
    
    pdfInput.addEventListener('change', (e) => {
        console.log('📄 PDF file selected:', e.target.files[0]?.name);
        handleFileSelection(e, 'pdf');
    });
    
    // Clear selection handler
    if (clearSelection) {
        clearSelection.addEventListener('click', clearFileSelection);
    }
    
    // Submit button handler
    if (submitBtn) {
        submitBtn.addEventListener('click', handleSubmit);
    }
    
    console.log('✅ Upload interface initialized successfully!');
}

// Handle file selection from any input method
function handleFileSelection(event, method) {
    const file = event.target.files[0];
    if (!file) return;
    
    uploadMethod = method;
    
    if (validateFile(file, method)) {
        selectedFile = file;
        showFilePreview(file, method);
        submitBtn.disabled = false;
    }
}

// File validation function
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
    previewArea.classList.remove('hidden');
    
    // Create preview content
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
        reader.onload = (e) => {
            filePreview.innerHTML = `
                <img src="${e.target.result}" alt="Preview" class="max-w-full max-h-64 mx-auto rounded-lg shadow-md">
                <p class="font-semibold text-gray-800 mt-3">${file.name}</p>
            `;
        };
        reader.readAsDataURL(file);
    }
    
    // Show file info
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
    
    showSuccess(`File selected via ${methodLabels[method].toLowerCase()}`);
}

// Clear file selection
function clearFileSelection() {
    selectedFile = null;
    uploadMethod = null;
    previewArea.classList.add('hidden');
    filePreview.innerHTML = '';
    fileInfo.innerHTML = '';
    submitBtn.disabled = true;
    
    // Reset all file inputs
    cameraInput.value = '';
    galleryInput.value = '';
    pdfInput.value = '';
    
    clearStatus();
}

// Handle form submission
function handleSubmit() {
    if (!selectedFile) {
        showError('Please select a file first.');
        return;
    }
    
    uploadFile(selectedFile);
}

// Upload file function
async function uploadFile(file) {
    if (!file) {
        showError('Please select a file first');
        return;
    }
    
    await submitInvoice(file);
}

function showFileSelected(file) {
    uploadStatus.innerHTML = `
        <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div class="flex items-center">
                <i class="fas fa-file-pdf text-blue-600 mr-2"></i>
                <span class="text-blue-800 font-medium">File selected: ${file.name}</span>
            </div>
            <div class="mt-2 text-sm text-blue-700">
                <p>Size: ${(file.size / 1024 / 1024).toFixed(2)} MB</p>
                <p>Ready to submit for processing</p>
            </div>
        </div>
    `;
}

async function submitInvoice(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    // Disable submit button and show processing
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Submitting...';
    
    uploadStatus.innerHTML = `
        <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <div class="flex items-center">
                <i class="fas fa-spinner fa-spin text-yellow-600 mr-2"></i>
                <span class="text-yellow-800 font-medium">Submitting ${file.name}...</span>
            </div>
        </div>
    `;
    
    try {
        console.log('📤 Submitting file to:', `${API_URL}/invoices/upload`);
        
        const response = await fetch(`${API_URL}/invoices/upload`, {
            method: 'POST',
            body: formData
        });
        
        console.log('📥 Response status:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('❌ Upload failed:', errorText);
            throw new Error(`Upload failed: ${response.status} - ${errorText}`);
        }
        
        const responseData = await response.json();
        console.log('✅ Upload successful:', responseData);
        
        const { invoice_id } = responseData;
        
        // Show success message
        uploadStatus.innerHTML = `
            <div class="bg-green-50 border border-green-200 rounded-lg p-4">
                <div class="flex items-center">
                    <i class="fas fa-check-circle text-green-600 mr-2"></i>
                    <span class="text-green-800 font-medium">Invoice submitted successfully!</span>
                </div>
                <div class="mt-2 text-sm text-green-700">
                    <p><strong>Invoice ID:</strong> ${invoice_id}</p>
                    <p>Your invoice is being processed in the background.</p>
                    <p>Processing typically takes 1-2 minutes.</p>
                </div>
            </div>
        `;
        
        // Reset form after 3 seconds
        setTimeout(() => {
            resetForm();
        }, 3000);
        
    } catch (error) {
        console.error('Submit error:', error);
        const errorMessage = error.message || 'Submission failed';
        showError('Submission failed: ' + errorMessage);
        
        // Re-enable submit button
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-paper-plane mr-2"></i>Submit Invoice';
    }
}

function resetForm() {
    selectedFile = null;
    uploadMethod = null;
    
    // Reset all file inputs
    if (cameraInput) cameraInput.value = '';
    if (galleryInput) galleryInput.value = '';
    if (pdfInput) pdfInput.value = '';
    
    // Hide preview area
    if (previewArea) previewArea.classList.add('hidden');
    if (filePreview) filePreview.innerHTML = '';
    if (fileInfo) fileInfo.innerHTML = '';
    
    uploadStatus.innerHTML = '';
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-paper-plane mr-2"></i>Process Invoice';
}

function showError(message) {
    uploadStatus.innerHTML = `
        <div class="bg-red-50 border border-red-200 rounded-lg p-4">
            <div class="flex items-center">
                <i class="fas fa-exclamation-circle text-red-600 mr-2"></i>
                <span class="text-red-800 font-medium">Error</span>
            </div>
            <p class="mt-2 text-sm text-red-700">${message}</p>
        </div>
    `;
    
    // Auto-hide error after 5 seconds
    setTimeout(() => {
        uploadStatus.innerHTML = '';
    }, 5000);
}

// Utility functions
function showSuccess(message) {
    uploadStatus.innerHTML = `
        <div class="bg-green-50 border border-green-200 rounded-lg p-4">
            <div class="flex items-center">
                <i class="fas fa-check-circle text-green-600 mr-2"></i>
                <span class="text-green-800 font-medium">Success</span>
            </div>
            <p class="mt-2 text-sm text-green-700">${message}</p>
        </div>
    `;
}

function clearStatus() {
    uploadStatus.innerHTML = '';
}
