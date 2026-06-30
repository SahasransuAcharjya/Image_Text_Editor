document.addEventListener('DOMContentLoaded', () => {
    const uploadZone = document.getElementById('upload-zone');
    const fileInput = document.getElementById('file-input');
    const imagePreviewContainer = document.getElementById('image-preview-container');
    const imagePreview = document.getElementById('image-preview');
    const clearBtn = document.getElementById('clear-btn');
    const scanningOverlay = document.getElementById('scanning-overlay');
    const scanStatus = document.getElementById('scan-status');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    const placeholderState = document.getElementById('placeholder-state');
    const blocksEditor = document.getElementById('blocks-editor');
    const editorActions = document.getElementById('editor-actions');
    const copyBtn = document.getElementById('copy-btn');
    const downloadBtn = document.getElementById('download-btn');
    const renderBtn = document.getElementById('render-btn');

    let currentFile = null;
    let extractedBlocks = [];

    uploadZone.addEventListener('click', () => fileInput.click());

    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('dragover');
    });

    uploadZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
    });

    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleFile(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files.length > 0) {
            handleFile(e.target.files[0]);
        }
    });

    clearBtn.addEventListener('click', () => {
        fileInput.value = '';
        imagePreview.src = '';
        currentFile = null;
        extractedBlocks = [];
        
        uploadZone.classList.remove('hidden');
        imagePreviewContainer.classList.add('hidden');
        placeholderState.classList.remove('hidden');
        blocksEditor.classList.add('hidden');
        blocksEditor.innerHTML = '';
        editorActions.classList.add('hidden');
    });

    function handleFile(file) {
        if (!file.type.startsWith('image/')) {
            alert('Please select a valid image file.');
            return;
        }

        currentFile = file;
        const reader = new FileReader();
        
        reader.onload = (e) => {
            imagePreview.src = e.target.result;
            uploadZone.classList.add('hidden');
            imagePreviewContainer.classList.remove('hidden');
            placeholderState.classList.add('hidden');
            
            processImage(file);
        };
        
        reader.readAsDataURL(file);
    }

    async function processImage(file) {
        scanningOverlay.classList.remove('hidden');
        blocksEditor.classList.add('hidden');
        editorActions.classList.add('hidden');
        blocksEditor.innerHTML = '';
        
        let progress = 0;
        const progressInterval = setInterval(() => {
            if (progress < 90) {
                progress += Math.random() * 15;
                if (progress > 90) progress = 90;
                progressBar.style.width = `${Math.round(progress)}%`;
                progressText.innerText = `${Math.round(progress)}%`;
                scanStatus.innerText = 'Extracting text via AI Engine...';
            }
        }, 300);

        try {
            const formData = new FormData();
            formData.append('image', file);

            const response = await fetch('http://localhost:5000/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to extract text');
            }

            const data = await response.json();
            extractedBlocks = data.blocks;
            
            clearInterval(progressInterval);
            progressBar.style.width = '100%';
            progressText.innerText = '100%';
            
            renderEditorBlocks();
            
        } catch (error) {
            console.error('OCR Error:', error);
            clearInterval(progressInterval);
            blocksEditor.innerHTML = `<div class="error-msg">Error: ${error.message}</div>`;
            blocksEditor.classList.remove('hidden');
        } finally {
            setTimeout(() => {
                scanningOverlay.classList.add('hidden');
                progressBar.style.width = '0%';
                progressText.innerText = '0%';
            }, 500);
        }
    }

    function renderEditorBlocks() {
        blocksEditor.innerHTML = '';
        
        if (extractedBlocks.length === 0) {
            blocksEditor.innerHTML = '<p style="color: var(--text-secondary); text-align: center; margin-top: 2rem;">No text found in the image.</p>';
        } else {
            extractedBlocks.forEach((block, index) => {
                // Store the original text for comparison later
                block.originalText = block.text;

                const blockDiv = document.createElement('div');
                blockDiv.className = 'text-block';
                
                const input = document.createElement('input');
                input.type = 'text';
                input.className = 'block-input';
                input.value = block.text;
                input.dataset.id = block.id;
                
                // Update local state when edited
                input.addEventListener('input', (e) => {
                    extractedBlocks[index].text = e.target.value;
                });
                
                blockDiv.appendChild(input);
                blocksEditor.appendChild(blockDiv);
            });
            editorActions.classList.remove('hidden');
        }
        
        blocksEditor.classList.remove('hidden');
    }

    // Render the final edited image
    renderBtn.addEventListener('click', async () => {
        if (!currentFile || extractedBlocks.length === 0) return;
        
        // ONLY send blocks that were actually changed!
        const changedBlocks = extractedBlocks.filter(b => b.text !== b.originalText);
        if (changedBlocks.length === 0) {
            alert('No changes detected. Edit some text first!');
            return;
        }

        const originalText = renderBtn.innerHTML;
        renderBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Rendering...';
        renderBtn.disabled = true;
        
        try {
            const formData = new FormData();
            formData.append('image', currentFile);
            formData.append('edits', JSON.stringify(changedBlocks));

            const response = await fetch('http://localhost:5000/render', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error('Failed to render image');
            }

            // Get image blob and display it
            const imageBlob = await response.blob();
            const imageUrl = URL.createObjectURL(imageBlob);
            
            imagePreview.src = imageUrl;
            
        } catch (error) {
            console.error('Render Error:', error);
            alert('Error rendering image: ' + error.message);
        } finally {
            renderBtn.innerHTML = originalText;
            renderBtn.disabled = false;
        }
    });

    // Copy to clipboard
    copyBtn.addEventListener('click', () => {
        const text = extractedBlocks.map(b => b.text).join('\n');
        if (!text) return;
        navigator.clipboard.writeText(text).then(() => {
            const originalHtml = copyBtn.innerHTML;
            copyBtn.innerHTML = '<i class="fa-solid fa-check" style="color: var(--success)"></i>';
            setTimeout(() => { copyBtn.innerHTML = originalHtml; }, 2000);
        });
    });

    // Download as txt
    downloadBtn.addEventListener('click', () => {
        const text = extractedBlocks.map(b => b.text).join('\n');
        if (!text) return;
        const blob = new Blob([text], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'extracted_text.txt';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    });
});
