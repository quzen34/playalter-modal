// PLAYALTER Web Interface JavaScript
class PlayAlterAPI {
    constructor() {
        this.baseURL = 'https://your-modal-app-url.com/api'; // Replace with your Modal deployment URL
        this.apiKey = '';
    }

    setApiKey(key) {
        this.apiKey = key;
    }

    async makeRequest(endpoint, method = 'GET', data = null, isFormData = false) {
        const headers = {};
        
        if (this.apiKey) {
            headers['Authorization'] = `Bearer ${this.apiKey}`;
        }

        if (!isFormData) {
            headers['Content-Type'] = 'application/json';
        }

        const config = {
            method: method,
            headers: headers
        };

        if (data) {
            config.body = isFormData ? data : JSON.stringify(data);
        }

        try {
            const response = await fetch(`${this.baseURL}${endpoint}`, config);
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API Request failed:', error);
            throw error;
        }
    }

    async testConnection() {
        return await this.makeRequest('/services/status');
    }

    async analyzeFace(imageBase64, includeMeasurements = true, include3DMesh = false) {
        return await this.makeRequest('/face/analyze', 'POST', {
            image_base64: imageBase64,
            include_measurements: includeMeasurements,
            include_3d_mesh: include3DMesh
        });
    }

    async generatePrivacyMask(imageBase64, maskType = 'blur', strength = 1.0, createLevels = false) {
        return await this.makeRequest('/privacy/mask', 'POST', {
            image_base64: imageBase64,
            mask_type: maskType,
            strength: strength,
            create_levels: createLevels
        });
    }

    async swapFaces(sourceBase64, targetBase64, sourceFaceIndex = 0, targetFaceIndex = 0) {
        return await this.makeRequest('/face/swap', 'POST', {
            source_image_base64: sourceBase64,
            target_image_base64: targetBase64,
            source_face_index: sourceFaceIndex,
            target_face_index: targetFaceIndex
        });
    }

    async checkCompatibility(sourceBase64, targetBase64) {
        const formData = new FormData();
        formData.append('source_image_base64', sourceBase64);
        formData.append('target_image_base64', targetBase64);
        
        return await this.makeRequest('/face/compatibility', 'POST', formData, true);
    }

    async processBatch(imagesBase64, operation, parameters = {}) {
        return await this.makeRequest('/batch/process', 'POST', {
            images_base64: imagesBase64,
            operation: operation,
            parameters: parameters
        });
    }
}

// Global API instance
const api = new PlayAlterAPI();

// Utility functions
function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = () => resolve(reader.result.split(',')[1]);
        reader.onerror = error => reject(error);
    });
}

function showLoading(elementId) {
    document.getElementById(elementId).classList.add('show');
}

function hideLoading(elementId) {
    document.getElementById(elementId).classList.remove('show');
}

function showError(elementId, message) {
    const errorElement = document.getElementById(elementId);
    errorElement.textContent = message;
    errorElement.style.display = 'block';
    setTimeout(() => {
        errorElement.style.display = 'none';
    }, 5000);
}

function showSuccess(elementId, message) {
    const successElement = document.getElementById(elementId);
    successElement.textContent = message;
    successElement.style.display = 'block';
    setTimeout(() => {
        successElement.style.display = 'none';
    }, 3000);
}

function clearResults(elementId) {
    document.getElementById(elementId).innerHTML = '';
}

// Image preview functions
function previewImage(input, previewId) {
    const preview = document.getElementById(previewId);
    
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = function(e) {
            preview.innerHTML = `
                <div style="margin: 10px 0;">
                    <img src="${e.target.result}" style="max-width: 200px; max-height: 200px; border-radius: 10px;">
                    <p style="margin-top: 5px; font-size: 0.9em; color: #666;">${input.files[0].name}</p>
                </div>
            `;
        };
        reader.readAsDataURL(input.files[0]);
    }
}

function previewBatchImages(input) {
    const preview = document.getElementById('batchPreview');
    preview.innerHTML = '';

    if (input.files.length > 10) {
        showError('batchError', 'Maximum 10 files allowed');
        input.value = '';
        return;
    }

    for (let i = 0; i < input.files.length; i++) {
        const file = input.files[i];
        const reader = new FileReader();
        reader.onload = function(e) {
            const imageDiv = document.createElement('div');
            imageDiv.style.cssText = 'display: inline-block; margin: 10px; text-align: center;';
            imageDiv.innerHTML = `
                <img src="${e.target.result}" style="width: 100px; height: 100px; object-fit: cover; border-radius: 5px;">
                <p style="font-size: 0.8em; color: #666; margin-top: 5px;">${file.name}</p>
            `;
            preview.appendChild(imageDiv);
        };
        reader.readAsDataURL(file);
    }
}

// Drag and drop functions
function handleDragOver(event) {
    event.preventDefault();
    event.currentTarget.classList.add('dragover');
}

function handleDrop(event, inputId) {
    event.preventDefault();
    event.currentTarget.classList.remove('dragover');
    
    const files = event.dataTransfer.files;
    if (files.length > 0) {
        const input = document.getElementById(inputId);
        input.files = files;
        
        if (inputId === 'batchFiles') {
            previewBatchImages(input);
        } else {
            const previewId = inputId.replace('File', 'Preview');
            previewImage(input, previewId);
        }
    }
}

// API functions
async function testConnection() {
    const apiKeyInput = document.getElementById('apiKey');
    api.setApiKey(apiKeyInput.value);

    try {
        const result = await api.testConnection();
        showSuccess('faceAnalysisSuccess', 'Connection successful! Services available: ' + result.supported_operations?.join(', '));
        console.log('Connection test result:', result);
    } catch (error) {
        showError('faceAnalysisError', 'Connection failed: ' + error.message);
    }
}

async function analyzeFace() {
    const fileInput = document.getElementById('faceAnalysisFile');
    const includeMeasurements = document.getElementById('includeMeasurements').checked;
    const include3DMesh = document.getElementById('include3DMesh').checked;

    if (!fileInput.files[0]) {
        showError('faceAnalysisError', 'Please select an image');
        return;
    }

    try {
        showLoading('faceAnalysisLoading');
        clearResults('faceAnalysisResults');

        const imageBase64 = await fileToBase64(fileInput.files[0]);
        const result = await api.analyzeFace(imageBase64, includeMeasurements, include3DMesh);

        hideLoading('faceAnalysisLoading');
        
        if (result.success) {
            displayFaceAnalysisResults(result);
            showSuccess('faceAnalysisSuccess', 'Face analysis completed successfully!');
        } else {
            showError('faceAnalysisError', 'Analysis failed: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        hideLoading('faceAnalysisLoading');
        showError('faceAnalysisError', 'Analysis failed: ' + error.message);
    }
}

function displayFaceAnalysisResults(result) {
    const resultsDiv = document.getElementById('faceAnalysisResults');
    let html = '<h4>Analysis Results</h4>';

    // Display measurements
    if (result.measurements) {
        html += '<div class="measurements"><h4>Face Measurements</h4>';
        for (const [key, value] of Object.entries(result.measurements)) {
            const displayKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            html += `<div class="measurement-item"><span>${displayKey}:</span><span>${typeof value === 'number' ? value.toFixed(3) : value}</span></div>`;
        }
        html += '</div>';
    }

    // Display FLAME parameters summary
    if (result.flame_parameters) {
        html += '<div class="measurements"><h4>FLAME Parameters</h4>';
        html += `<div class="measurement-item"><span>Shape Parameters:</span><span>${result.flame_parameters.shape_params[0]?.length || 0}</span></div>`;
        html += `<div class="measurement-item"><span>Expression Parameters:</span><span>${result.flame_parameters.exp_params[0]?.length || 0}</span></div>`;
        html += `<div class="measurement-item"><span>Pose Parameters:</span><span>${result.flame_parameters.pose_params[0]?.length || 0}</span></div>`;
        html += '</div>';
    }

    resultsDiv.innerHTML = html;
}

async function generatePrivacyMask() {
    const fileInput = document.getElementById('privacyMaskFile');
    const maskType = document.getElementById('maskType').value;
    const strength = parseFloat(document.getElementById('maskStrength').value);
    const createLevels = document.getElementById('createLevels').checked;

    if (!fileInput.files[0]) {
        showError('privacyMaskError', 'Please select an image');
        return;
    }

    try {
        showLoading('privacyMaskLoading');
        clearResults('privacyMaskResults');

        const imageBase64 = await fileToBase64(fileInput.files[0]);
        const result = await api.generatePrivacyMask(imageBase64, maskType, strength, createLevels);

        hideLoading('privacyMaskLoading');

        if (result.success) {
            displayPrivacyMaskResults(result, createLevels);
            showSuccess('privacyMaskSuccess', 'Privacy mask generated successfully!');
        } else {
            showError('privacyMaskError', 'Mask generation failed: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        hideLoading('privacyMaskLoading');
        showError('privacyMaskError', 'Mask generation failed: ' + error.message);
    }
}

function displayPrivacyMaskResults(result, showLevels) {
    const resultsDiv = document.getElementById('privacyMaskResults');
    let html = '<div class="result-images">';

    if (showLevels && result.privacy_levels) {
        for (const [level, imageBase64] of Object.entries(result.privacy_levels)) {
            html += `
                <div class="result-item">
                    <h4>${level.charAt(0).toUpperCase() + level.slice(1)} Level</h4>
                    <img src="data:image/jpeg;base64,${imageBase64}" alt="${level} privacy mask">
                    <button class="btn" onclick="downloadImage('${imageBase64}', 'privacy_mask_${level}.jpg')">Download</button>
                </div>
            `;
        }
    } else if (result.masked_image) {
        html += `
            <div class="result-item">
                <h4>Privacy Masked Image</h4>
                <img src="data:image/jpeg;base64,${result.masked_image}" alt="Privacy masked">
                <button class="btn" onclick="downloadImage('${result.masked_image}', 'privacy_masked.jpg')">Download</button>
            </div>
        `;

        // Display measurements
        if (result.measurements) {
            html += '<div class="measurements"><h4>Face Measurements Used</h4>';
            for (const [key, value] of Object.entries(result.measurements)) {
                if (typeof value === 'number') {
                    const displayKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                    html += `<div class="measurement-item"><span>${displayKey}:</span><span>${value.toFixed(3)}</span></div>`;
                }
            }
            html += '</div>';
        }
    }

    html += '</div>';
    resultsDiv.innerHTML = html;
}

async function checkCompatibility() {
    const sourceInput = document.getElementById('sourceFile');
    const targetInput = document.getElementById('targetFile');

    if (!sourceInput.files[0] || !targetInput.files[0]) {
        showError('faceSwapError', 'Please select both source and target images');
        return;
    }

    try {
        showLoading('faceSwapLoading');

        const sourceBase64 = await fileToBase64(sourceInput.files[0]);
        const targetBase64 = await fileToBase64(targetInput.files[0]);
        
        const result = await api.checkCompatibility(sourceBase64, targetBase64);

        hideLoading('faceSwapLoading');

        if (result.success) {
            displayCompatibilityResults(result);
            showSuccess('faceSwapSuccess', 'Compatibility check completed!');
        } else {
            showError('faceSwapError', 'Compatibility check failed: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        hideLoading('faceSwapLoading');
        showError('faceSwapError', 'Compatibility check failed: ' + error.message);
    }
}

function displayCompatibilityResults(result) {
    const resultsDiv = document.getElementById('faceSwapResults');
    
    const rating = result.compatibility_rating || 'Unknown';
    const ratingColor = {
        'Excellent': '#4caf50',
        'Good': '#8bc34a',
        'Fair': '#ff9800',
        'Poor': '#f44336'
    }[rating] || '#666';

    const html = `
        <div class="measurements">
            <h4>Compatibility Analysis</h4>
            <div class="measurement-item">
                <span>Overall Rating:</span>
                <span style="color: ${ratingColor}; font-weight: bold;">${rating}</span>
            </div>
            <div class="measurement-item">
                <span>Similarity Score:</span>
                <span>${(result.similarity_score * 100).toFixed(1)}%</span>
            </div>
            <div class="measurement-item">
                <span>Size Compatibility:</span>
                <span>${(result.size_compatibility * 100).toFixed(1)}%</span>
            </div>
            <div class="measurement-item">
                <span>Source Face Quality:</span>
                <span>${(result.source_face_quality * 100).toFixed(1)}%</span>
            </div>
            <div class="measurement-item">
                <span>Target Face Quality:</span>
                <span>${(result.target_face_quality * 100).toFixed(1)}%</span>
            </div>
        </div>
    `;
    
    resultsDiv.innerHTML = html;
}

async function performFaceSwap() {
    const sourceInput = document.getElementById('sourceFile');
    const targetInput = document.getElementById('targetFile');
    const sourceFaceIndex = parseInt(document.getElementById('sourceFaceIndex').value);
    const targetFaceIndex = parseInt(document.getElementById('targetFaceIndex').value);

    if (!sourceInput.files[0] || !targetInput.files[0]) {
        showError('faceSwapError', 'Please select both source and target images');
        return;
    }

    try {
        showLoading('faceSwapLoading');
        clearResults('faceSwapResults');

        const sourceBase64 = await fileToBase64(sourceInput.files[0]);
        const targetBase64 = await fileToBase64(targetInput.files[0]);
        
        const result = await api.swapFaces(sourceBase64, targetBase64, sourceFaceIndex, targetFaceIndex);

        hideLoading('faceSwapLoading');

        if (result.success) {
            displayFaceSwapResults(result);
            showSuccess('faceSwapSuccess', 'Face swap completed successfully!');
        } else {
            showError('faceSwapError', 'Face swap failed: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        hideLoading('faceSwapLoading');
        showError('faceSwapError', 'Face swap failed: ' + error.message);
    }
}

function displayFaceSwapResults(result) {
    const resultsDiv = document.getElementById('faceSwapResults');
    
    const html = `
        <div class="result-images">
            <div class="result-item">
                <h4>Face Swapped Result</h4>
                <img src="data:image/jpeg;base64,${result.result_image}" alt="Face swapped">
                <p>Source faces: ${result.source_face_count} | Target faces: ${result.target_face_count}</p>
                <button class="btn" onclick="downloadImage('${result.result_image}', 'face_swapped.jpg')">Download</button>
            </div>
        </div>
    `;
    
    resultsDiv.innerHTML = html;
}

async function processBatch() {
    const filesInput = document.getElementById('batchFiles');
    const operation = document.getElementById('batchOperation').value;

    if (!filesInput.files.length) {
        showError('batchError', 'Please select images for batch processing');
        return;
    }

    try {
        showLoading('batchLoading');
        clearResults('batchResults');

        // Convert all files to base64
        const imagesBase64 = [];
        for (let i = 0; i < filesInput.files.length; i++) {
            const base64 = await fileToBase64(filesInput.files[i]);
            imagesBase64.push(base64);
        }

        // Set parameters based on operation
        const parameters = {};
        if (operation === 'privacy_mask') {
            parameters.mask_type = 'blur';
            parameters.strength = 1.0;
        }

        const result = await api.processBatch(imagesBase64, operation, parameters);

        hideLoading('batchLoading');

        if (result.success) {
            displayBatchResults(result, operation);
            showSuccess('batchSuccess', `Batch processing completed! ${result.successful_count}/${result.total_processed} images processed successfully.`);
        } else {
            showError('batchError', 'Batch processing failed: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        hideLoading('batchLoading');
        showError('batchError', 'Batch processing failed: ' + error.message);
    }
}

function displayBatchResults(result, operation) {
    const resultsDiv = document.getElementById('batchResults');
    let html = '<div class="result-images">';

    result.results.forEach((item, index) => {
        if (item.success) {
            if (operation === 'privacy_mask' && item.result_image) {
                html += `
                    <div class="result-item">
                        <h4>Image ${index + 1}</h4>
                        <img src="data:image/jpeg;base64,${item.result_image}" alt="Processed image ${index + 1}">
                        <button class="btn" onclick="downloadImage('${item.result_image}', 'batch_${index + 1}.jpg')">Download</button>
                    </div>
                `;
            } else if (operation === 'face_analysis') {
                html += `
                    <div class="result-item">
                        <h4>Analysis ${index + 1}</h4>
                        <div class="measurements">
                            <div class="measurement-item">
                                <span>Faces detected:</span>
                                <span>${item.landmarks ? 1 : 0}</span>
                            </div>
                            <div class="measurement-item">
                                <span>Measurements:</span>
                                <span>${Object.keys(item.measurements || {}).length}</span>
                            </div>
                        </div>
                    </div>
                `;
            }
        } else {
            html += `
                <div class="result-item">
                    <h4>Image ${index + 1} - Error</h4>
                    <p style="color: #f44336;">${item.error}</p>
                </div>
            `;
        }
    });

    html += '</div>';
    resultsDiv.innerHTML = html;
}

// Utility function to download images
function downloadImage(base64Data, filename) {
    const link = document.createElement('a');
    link.href = 'data:image/jpeg;base64,' + base64Data;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    console.log('PLAYALTER Web Interface Initialized');
    
    // Set up drag and drop for all upload areas
    const uploadAreas = document.querySelectorAll('.upload-area');
    uploadAreas.forEach(area => {
        area.addEventListener('dragenter', (e) => {
            e.preventDefault();
            area.classList.add('dragover');
        });
        
        area.addEventListener('dragleave', (e) => {
            e.preventDefault();
            area.classList.remove('dragover');
        });
    });
});