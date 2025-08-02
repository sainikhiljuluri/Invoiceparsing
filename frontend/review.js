// Human Review Dashboard JavaScript
const API_URL = 'http://localhost:8000/api/v1';

// DOM elements
const queueList = document.getElementById('queueList');
const reviewInterface = document.getElementById('reviewInterface');
const statsDisplay = document.getElementById('statsDisplay');
const refreshBtn = document.getElementById('refreshBtn');
const priorityFilter = document.getElementById('priorityFilter');
const filterBtn = document.getElementById('filterBtn');
const loadingModal = document.getElementById('loadingModal');
const successModal = document.getElementById('successModal');
const successMessage = document.getElementById('successMessage');
const successOkBtn = document.getElementById('successOkBtn');

// Current state
let currentQueue = [];
let currentItem = null;
let currentItemDetails = null;

// Initialize the dashboard
document.addEventListener('DOMContentLoaded', () => {
    console.log('Human Review Dashboard loaded');
    loadStats();
    loadQueue();
    
    // Event listeners
    refreshBtn.addEventListener('click', () => {
        loadQueue();
        loadStats();
    });
    
    filterBtn.addEventListener('click', () => {
        loadQueue();
    });
    
    successOkBtn.addEventListener('click', () => {
        hideModal('successModal');
        loadQueue(); // Refresh queue after action
        loadStats(); // Refresh stats
    });
});

async function loadStats() {
    try {
        const response = await axios.get(`${API_URL}/review/stats`);
        const stats = response.data;
        
        statsDisplay.innerHTML = `
            <div class="flex items-center space-x-4">
                <span class="bg-red-100 text-red-800 px-2 py-1 rounded text-xs">
                    <i class="fas fa-exclamation-triangle mr-1"></i>
                    ${stats.queue_stats.high_priority} High Priority
                </span>
                <span class="bg-yellow-100 text-yellow-800 px-2 py-1 rounded text-xs">
                    <i class="fas fa-clock mr-1"></i>
                    ${stats.queue_stats.pending} Pending
                </span>
                <span class="bg-green-100 text-green-800 px-2 py-1 rounded text-xs">
                    <i class="fas fa-check mr-1"></i>
                    ${stats.queue_stats.approved} Approved
                </span>
            </div>
        `;
    } catch (error) {
        console.error('Failed to load stats:', error);
        statsDisplay.innerHTML = '<span class="text-red-600">Failed to load stats</span>';
    }
}

async function loadQueue() {
    try {
        const priority = priorityFilter.value;
        const params = new URLSearchParams();
        if (priority) params.append('priority', priority);
        
        const response = await axios.get(`${API_URL}/review/queue?${params.toString()}`);
        currentQueue = response.data;
        
        renderQueue();
    } catch (error) {
        console.error('Failed to load queue:', error);
        queueList.innerHTML = `
            <div class="p-4 text-center text-red-600">
                <i class="fas fa-exclamation-triangle mb-2"></i>
                <p>Failed to load review queue</p>
            </div>
        `;
    }
}

function renderQueue() {
    if (currentQueue.length === 0) {
        queueList.innerHTML = `
            <div class="p-4 text-center text-gray-500">
                <i class="fas fa-inbox text-2xl mb-2"></i>
                <p>No items in review queue</p>
            </div>
        `;
        return;
    }
    
    queueList.innerHTML = currentQueue.map(item => {
        const productInfo = item.product_info;
        const priorityClass = item.priority === 1 ? 'border-l-red-500' : 'border-l-yellow-500';
        const priorityIcon = item.priority === 1 ? 'fas fa-exclamation-triangle text-red-500' : 'fas fa-clock text-yellow-500';
        
        return `
            <div class="queue-item p-4 cursor-pointer hover:bg-gray-50 border-l-4 ${priorityClass}" 
                 onclick="selectItem('${item.id}')">
                <div class="flex items-start justify-between">
                    <div class="flex-1">
                        <div class="flex items-center mb-1">
                            <i class="${priorityIcon} mr-2"></i>
                            <span class="font-medium text-sm text-gray-900">
                                ${productInfo.product_name || 'Unknown Product'}
                            </span>
                        </div>
                        <div class="text-xs text-gray-500 space-y-1">
                            <p><strong>Invoice:</strong> ${productInfo.invoice_id}</p>
                            <p><strong>Confidence:</strong> ${(productInfo.confidence * 100).toFixed(1)}%</p>
                            <p><strong>Strategy:</strong> ${productInfo.strategy}</p>
                        </div>
                    </div>
                    <div class="text-xs text-gray-400">
                        ${new Date(item.created_at).toLocaleDateString()}
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

async function selectItem(reviewId) {
    try {
        // Highlight selected item
        document.querySelectorAll('.queue-item').forEach(item => {
            item.classList.remove('bg-blue-50', 'border-l-blue-500');
        });
        
        event.target.closest('.queue-item').classList.add('bg-blue-50', 'border-l-blue-500');
        
        // Load item details
        const response = await axios.get(`${API_URL}/review/item/${reviewId}`);
        currentItemDetails = response.data;
        currentItem = currentItemDetails.review_item;
        
        renderReviewInterface();
    } catch (error) {
        console.error('Failed to load item details:', error);
        showError('Failed to load item details');
    }
}

function renderReviewInterface() {
    if (!currentItem || !currentItemDetails) return;
    
    const productInfo = currentItem.product_info;
    const suggestions = currentItemDetails.suggestions || [];
    
    reviewInterface.innerHTML = `
        <div class="space-y-6">
            <!-- Original Invoice Data -->
            <div>
                <h3 class="text-lg font-semibold text-gray-900 mb-3">Invoice Item Details</h3>
                <div class="bg-gray-50 rounded-lg p-4 space-y-2">
                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <p class="text-sm font-medium text-gray-700">Product Name:</p>
                            <p class="text-sm text-gray-900">${productInfo.product_name}</p>
                        </div>
                        <div>
                            <p class="text-sm font-medium text-gray-700">Invoice:</p>
                            <p class="text-sm text-gray-900">${productInfo.invoice_id}</p>
                        </div>
                        <div>
                            <p class="text-sm font-medium text-gray-700">Units:</p>
                            <p class="text-sm text-gray-900">${productInfo.metadata?.units || 'N/A'}</p>
                        </div>
                        <div>
                            <p class="text-sm font-medium text-gray-700">Cost per Unit:</p>
                            <p class="text-sm text-gray-900">₹${productInfo.metadata?.cost_per_unit || 'N/A'}</p>
                        </div>
                        <div>
                            <p class="text-sm font-medium text-gray-700">AI Confidence:</p>
                            <p class="text-sm text-gray-900">${(productInfo.confidence * 100).toFixed(1)}%</p>
                        </div>
                        <div>
                            <p class="text-sm font-medium text-gray-700">Vendor:</p>
                            <p class="text-sm text-gray-900">${productInfo.metadata?.vendor || 'Unknown'}</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- AI Suggestions -->
            <div>
                <h3 class="text-lg font-semibold text-gray-900 mb-3">AI Suggestions</h3>
                ${suggestions.length > 0 ? renderSuggestions(suggestions) : '<p class="text-gray-500">No suggestions available</p>'}
            </div>

            <!-- Action Buttons -->
            <div class="flex flex-wrap gap-3 pt-4 border-t">
                <button onclick="showCreateNewProductForm()" 
                        class="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors">
                    <i class="fas fa-plus mr-2"></i>Create New Product
                </button>
                <button onclick="rejectMatch()" 
                        class="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors">
                    <i class="fas fa-times mr-2"></i>Reject / Skip
                </button>
                <button onclick="showManualSearchForm()" 
                        class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors">
                    <i class="fas fa-search mr-2"></i>Manual Search
                </button>
            </div>
        </div>
    `;
}

function renderSuggestions(suggestions) {
    return `
        <div class="space-y-3">
            ${suggestions.map((suggestion, index) => `
                <div class="border rounded-lg p-4 hover:bg-gray-50">
                    <div class="flex items-start justify-between">
                        <div class="flex-1">
                            <h4 class="font-medium text-gray-900">${suggestion.name}</h4>
                            <div class="mt-1 text-sm text-gray-600 space-y-1">
                                ${suggestion.product_details ? `
                                    <p><strong>Brand:</strong> ${suggestion.product_details.brand || 'N/A'}</p>
                                    <p><strong>Category:</strong> ${suggestion.product_details.category || 'N/A'}</p>
                                    <p><strong>Current Cost:</strong> ₹${suggestion.product_details.cost_per_unit || 'N/A'}</p>
                                ` : ''}
                                <p><strong>Match Score:</strong> ${(suggestion.score * 100).toFixed(1)}%</p>
                            </div>
                        </div>
                        <button onclick="approveMatch('${suggestion.product_id || suggestion.id}')" 
                                class="bg-green-600 text-white px-3 py-1 rounded text-sm hover:bg-green-700">
                            <i class="fas fa-check mr-1"></i>Approve
                        </button>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

async function approveMatch(productId) {
    if (!currentItem) return;
    
    try {
        showModal('loadingModal');
        
        const response = await axios.post(`${API_URL}/review/approve/${currentItem.id}`, {
            product_id: productId,
            create_mapping: true,
            confidence_override: 1.0
        });
        
        hideModal('loadingModal');
        showSuccess('Match approved successfully! The product mapping has been saved.');
        
        // Clear current selection
        currentItem = null;
        currentItemDetails = null;
        reviewInterface.innerHTML = `
            <div class="text-center text-gray-500 py-12">
                <i class="fas fa-check-circle text-green-500 text-4xl mb-4"></i>
                <p class="text-lg">Item approved! Select another item to continue reviewing.</p>
            </div>
        `;
        
    } catch (error) {
        hideModal('loadingModal');
        console.error('Failed to approve match:', error);
        showError('Failed to approve match: ' + (error.response?.data?.detail || error.message));
    }
}

async function rejectMatch() {
    if (!currentItem) return;
    
    const reason = prompt('Please provide a reason for rejection (optional):') || 'No reason provided';
    
    try {
        showModal('loadingModal');
        
        const response = await axios.post(`${API_URL}/review/reject/${currentItem.id}`, {
            reason: reason,
            create_mapping: false
        });
        
        hideModal('loadingModal');
        showSuccess('Item rejected and removed from queue.');
        
        // Clear current selection
        currentItem = null;
        currentItemDetails = null;
        reviewInterface.innerHTML = `
            <div class="text-center text-gray-500 py-12">
                <i class="fas fa-times-circle text-red-500 text-4xl mb-4"></i>
                <p class="text-lg">Item rejected! Select another item to continue reviewing.</p>
            </div>
        `;
        
    } catch (error) {
        hideModal('loadingModal');
        console.error('Failed to reject match:', error);
        showError('Failed to reject match: ' + (error.response?.data?.detail || error.message));
    }
}

function showCreateNewProductForm() {
    if (!currentItem) return;
    
    const productInfo = currentItem.product_info;
    
    const formHtml = `
        <div class="space-y-4">
            <h4 class="font-semibold text-gray-900">Create New Product</h4>
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">Product Name</label>
                    <input type="text" id="newProductName" value="${productInfo.product_name}" 
                           class="w-full border rounded px-3 py-2">
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">Brand</label>
                    <input type="text" id="newProductBrand" placeholder="Enter brand name" 
                           class="w-full border rounded px-3 py-2">
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">Category</label>
                    <input type="text" id="newProductCategory" placeholder="Enter category" 
                           class="w-full border rounded px-3 py-2">
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">Unit Type</label>
                    <select id="newProductUnitType" class="w-full border rounded px-3 py-2">
                        <option value="piece">Piece</option>
                        <option value="kg">Kilogram</option>
                        <option value="liter">Liter</option>
                        <option value="pack">Pack</option>
                        <option value="box">Box</option>
                    </select>
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">Cost per Unit (₹)</label>
                    <input type="number" id="newProductCost" value="${productInfo.metadata?.cost_per_unit || ''}" 
                           step="0.01" class="w-full border rounded px-3 py-2">
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">Vendor Key</label>
                    <input type="text" id="newProductVendor" value="${productInfo.metadata?.vendor || ''}" 
                           class="w-full border rounded px-3 py-2">
                </div>
            </div>
            <div class="flex gap-3">
                <button onclick="createNewProduct()" 
                        class="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">
                    <i class="fas fa-plus mr-2"></i>Create Product
                </button>
                <button onclick="renderReviewInterface()" 
                        class="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700">
                    Cancel
                </button>
            </div>
        </div>
    `;
    
    reviewInterface.innerHTML = formHtml;
}

async function createNewProduct() {
    if (!currentItem) return;
    
    const productData = {
        name: document.getElementById('newProductName').value,
        brand: document.getElementById('newProductBrand').value,
        category: document.getElementById('newProductCategory').value,
        unit_type: document.getElementById('newProductUnitType').value,
        cost_per_unit: parseFloat(document.getElementById('newProductCost').value),
        vendor_key: document.getElementById('newProductVendor').value
    };
    
    // Validate required fields
    if (!productData.name || !productData.brand || !productData.category) {
        showError('Please fill in all required fields (Name, Brand, Category)');
        return;
    }
    
    try {
        showModal('loadingModal');
        
        const response = await axios.post(`${API_URL}/review/create-product/${currentItem.id}`, productData);
        
        hideModal('loadingModal');
        showSuccess(`New product "${productData.name}" created successfully!`);
        
        // Clear current selection
        currentItem = null;
        currentItemDetails = null;
        reviewInterface.innerHTML = `
            <div class="text-center text-gray-500 py-12">
                <i class="fas fa-plus-circle text-green-500 text-4xl mb-4"></i>
                <p class="text-lg">New product created! Select another item to continue reviewing.</p>
            </div>
        `;
        
    } catch (error) {
        hideModal('loadingModal');
        console.error('Failed to create new product:', error);
        showError('Failed to create new product: ' + (error.response?.data?.detail || error.message));
    }
}

function showManualSearchForm() {
    // This would implement a manual product search interface
    // For now, show a simple alert
    alert('Manual search feature coming soon! Use the suggestions above or create a new product.');
}

// Utility functions
function showModal(modalId) {
    document.getElementById(modalId).classList.remove('hidden');
    document.getElementById(modalId).classList.add('flex');
}

function hideModal(modalId) {
    document.getElementById(modalId).classList.add('hidden');
    document.getElementById(modalId).classList.remove('flex');
}

function showSuccess(message) {
    successMessage.textContent = message;
    showModal('successModal');
}

function showError(message) {
    alert('Error: ' + message); // Simple error display for now
}
