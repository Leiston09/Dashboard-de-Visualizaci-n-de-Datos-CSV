let myChart = null;

document.addEventListener('DOMContentLoaded', () => {
    console.log('¡CSV Visualizer cargado!');
    
    // 1. Configuración de Drag & Drop
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file');
    const fileInfo = document.getElementById('file-info');
    const uploadForm = document.getElementById('upload-form');

    if (dropZone && fileInput) {
        // Al hacer clic en la zona, disparar el input
        dropZone.addEventListener('click', () => fileInput.click());

        // Eventos de arrastre
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                dropZone.classList.add('highlight');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                dropZone.classList.remove('highlight');
            }, false);
        });

        // Al soltar el archivo
        dropZone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files.length > 0) {
                fileInput.files = files;
                updateFileInfo(files[0]);
            }
        }, false);

        // Al seleccionar vía explorador
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                updateFileInfo(e.target.files[0]);
            }
        });
    }

    function updateFileInfo(file) {
        if (file) {
            fileInfo.textContent = `Archivo seleccionado: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
            fileInfo.style.color = '#fff';
        }
    }

    // 2. Carga inicial de datos si hay un archivo activo
    if (window.currentFilename) {
        loadFileData(window.currentFilename);
    }

    // 3. Manejo de botones de control de gráfica
    const updateBtn = document.getElementById('update-chart');
    const exportBtn = document.getElementById('export-png');

    if (updateBtn) {
        updateBtn.addEventListener('click', () => {
            renderChart();
        });
    }

    if (exportBtn) {
        exportBtn.addEventListener('click', () => {
            exportToPNG();
        });
    }
});

/**
 * Muestra una alerta dinámica en el contenedor de alertas
 */
function showAlert(message, type = 'error') {
    const container = document.getElementById('alert-container');
    if (!container) {
        // Si no existe el contenedor (ej: primera carga sin mensajes flash), crearlo
        const main = document.querySelector('.main-content');
        const newContainer = document.createElement('div');
        newContainer.className = 'alert-container';
        newContainer.id = 'alert-container';
        main.prepend(newContainer);
        showAlert(message, type);
        return;
    }

    const alert = document.createElement('div');
    alert.className = `alert ${type}`;
    alert.innerHTML = `
        <span>${message}</span>
        <button class="close-alert" onclick="this.parentElement.remove()">&times;</button>
    `;
    container.appendChild(alert);

    // Auto-eliminar después de 5 segundos
    setTimeout(() => {
        if (alert.parentElement) alert.remove();
    }, 5000);
}

/**
 * Carga los metadatos del archivo para poblar los dropdowns de ejes
 */
async function loadFileData(filename) {
    try {
        const response = await fetch(`/process?file=${encodeURIComponent(filename)}&json=true`, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        const data = await response.json();

        if (data.error) {
            showAlert(data.error);
            console.error(data.error);
            return;
        }

        // Poblar Selects de Ejes
        const selectX = document.getElementById('axis-x');
        const selectY = document.getElementById('axis-y');
        
        // Limpiar
        selectX.innerHTML = '<option value="">Selecciona columna...</option>';
        selectY.innerHTML = '<option value="">Selecciona columna...</option>';

        data.analisis_columnas.forEach(col => {
            const optX = document.createElement('option');
            optX.value = col.columna;
            optX.textContent = `${col.columna} (${col.tipo_detectado})`;
            selectX.appendChild(optX);

            const optY = document.createElement('option');
            optY.value = col.columna;
            optY.textContent = `${col.columna} (${col.tipo_detectado})`;
            selectY.appendChild(optY);
        });

        // Mostrar controles
        document.getElementById('controls-section').style.display = 'block';
        document.getElementById('canvas-container').style.display = 'block';
        document.getElementById('chart-placeholder').style.display = 'none';

        // Guardar datos en window para acceso rápido al graficar
        window.activeCSVData = data;
        
    } catch (err) {
        showAlert('Error de conexión al cargar los datos del archivo.');
        console.error('Error cargando datos del archivo:', err);
    }
}

/**
 * Renderiza la gráfica usando Chart.js
 */
async function renderChart() {
    const filename = window.currentFilename;
    const type = document.getElementById('chart-type').value;
    const colX = document.getElementById('axis-x').value;
    const colY = document.getElementById('axis-y').value;

    if (!colX || !colY) {
        showAlert('Por favor selecciona ambos ejes para graficar.', 'info');
        return;
    }

    try {
        // En un caso real, pediríamos los datos completos o agregados al servidor
        // Para este ejemplo, usamos la previsualización o pedimos un endpoint que devuelva los datos crudos
        const response = await fetch(`/process?file=${encodeURIComponent(filename)}&json=true`, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        const data = await response.json();
        
        if (data.error) {
            showAlert(data.error);
            return;
        }
        
        // Obtener índices de las columnas seleccionadas
        const idxX = data.preview_headers.indexOf(colX);
        const idxY = data.preview_headers.indexOf(colY);

        // Extraer etiquetas y valores (limitado a lo que el servidor devuelve en preview_rows por ahora)
        // Nota: En una app real, el servidor debería devolver el set completo de datos para graficar
        const labels = data.preview_rows.map(row => row[idxX]);
        const values = data.preview_rows.map(row => {
            const val = parseFloat(row[idxY]);
            return isNaN(val) ? 0 : val;
        });

        const ctx = document.getElementById('mainChart').getContext('2d');

        // Destruir gráfica anterior si existe
        if (myChart) {
            myChart.destroy();
        }

        const config = {
            type: type,
            data: {
                labels: labels,
                datasets: [{
                    label: `${colY} vs ${colX}`,
                    data: values,
                    backgroundColor: [
                        'rgba(79, 70, 229, 0.6)',
                        'rgba(14, 165, 233, 0.6)',
                        'rgba(16, 185, 129, 0.6)',
                        'rgba(245, 158, 11, 0.6)',
                        'rgba(239, 68, 68, 0.6)'
                    ],
                    borderColor: 'rgba(79, 70, 229, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: type !== 'pie' ? {
                    y: { beginAtZero: true }
                } : {},
                plugins: {
                    legend: { position: 'top' },
                    title: { display: true, text: `Análisis de ${colY}` }
                }
            }
        };

        // Si es dispersión, el formato de data es distinto {x, y}
        if (type === 'scatter') {
            config.data.datasets[0].data = data.preview_rows.map(row => ({
                x: parseFloat(row[idxX]) || 0,
                y: parseFloat(row[idxY]) || 0
            }));
            config.data.labels = null;
        }

        myChart = new Chart(ctx, config);

    } catch (err) {
        console.error('Error al generar la gráfica:', err);
        alert('Error al procesar los datos para la gráfica.');
    }
}

/**
 * Exporta el canvas actual como imagen PNG
 */
function exportToPNG() {
    const canvas = document.getElementById('mainChart');
    if (!canvas) return;

    const link = document.createElement('a');
    link.download = `grafica_${window.currentFilename || 'export'}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
}

/**
 * Función global para seleccionar un archivo de la lista
 */
function selectFile(filename) {
    window.currentFilename = filename;
    
    // Actualizar UI
    document.getElementById('current-file-display').innerHTML = `Archivo activo: <strong>${filename}</strong>`;
    
    // Marcar como activo en la lista
    document.querySelectorAll('.file-item').forEach(el => el.classList.remove('active'));
    document.querySelector(`[data-filename="${filename}"]`)?.classList.add('active');

    // Cargar sus metadatos
    loadFileData(filename);
}
