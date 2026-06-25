// ============================================================
// VARIABLES GLOBALES
// ============================================================
let myChart = null;
let currentPage = 1;
let rowsPerPage = 10;
let fullTableData = [];
let currentFileData = null;
let showFullTable = false;

// ============================================================
// VARIABLES DE AGRUPACIÓN
// ============================================================
let currentGroupSize = 1;
const GROUP_OPTIONS = [1, 5, 10, 20, 50];
let currentGroupIndex = 0;
let showGroupControls = false;

// ============================================================
// FUNCIÓN: ACTUALIZAR CONTROLES DE AGRUPACIÓN (DEFINIDA PRIMERO)
// ============================================================
function updateGroupControls() {
    const size = GROUP_OPTIONS[currentGroupIndex];
    currentGroupSize = size;
    
    // Barra lateral
    const groupDisplay = document.getElementById('group-display');
    if (groupDisplay) groupDisplay.textContent = size + ' en ' + size;
    
    const groupMinus = document.getElementById('group-minus');
    const groupPlus = document.getElementById('group-plus');
    if (groupMinus) groupMinus.disabled = currentGroupIndex <= 0;
    if (groupPlus) groupPlus.disabled = currentGroupIndex >= GROUP_OPTIONS.length - 1;
    
    const groupInfo = document.getElementById('group-info');
    if (groupInfo) {
        groupInfo.textContent = size === 1 ? 'Sin agrupación (1 en 1)' : 'Agrupado de ' + size + ' en ' + size;
    }
    
    // Controles de la gráfica
    const groupDisplayChart = document.getElementById('group-display-chart');
    if (groupDisplayChart) groupDisplayChart.textContent = size + ' en ' + size;
    
    const groupMinusChart = document.getElementById('group-minus-chart');
    const groupPlusChart = document.getElementById('group-plus-chart');
    if (groupMinusChart) groupMinusChart.disabled = currentGroupIndex <= 0;
    if (groupPlusChart) groupPlusChart.disabled = currentGroupIndex >= GROUP_OPTIONS.length - 1;
    
    // Mostrar/ocultar controles en la gráfica
    const groupControls = document.getElementById('group-controls');
    if (groupControls) {
        groupControls.style.display = showGroupControls ? 'flex' : 'none';
    }
}

// ============================================================
// INICIALIZACIÓN
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    console.log('📊 CSV Visualizer cargado');

    document.getElementById('stats-container').innerHTML = '';
    document.getElementById('preview-table-container').innerHTML = '';

    // ============================================================
    // MANEJO DE UPLOAD CON FETCH
    // ============================================================
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file');
    const uploadForm = document.getElementById('upload-form');

    async function uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);
        
        dropZone.innerHTML = `
            <div class="upload-icon">⏳</div>
            <p class="mb-1">Subiendo archivo...</p>
            <small>${file.name}</small>
        `;
        dropZone.style.borderColor = '#f39c12';
        
        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    console.log('✅ Archivo subido:', data.filename);
                    // @ts-ignore
                    window.currentFilename = data.filename;
                    
                    dropZone.innerHTML = `
                        <div class="upload-icon">✅</div>
                        <p class="mb-1">¡Archivo cargado!</p>
                        <small>${data.filename}</small>
                    `;
                    dropZone.style.borderColor = '#27ae60';
                    
                    await loadFileData(data.filename);
                    await loadFileList();
                    
                    if (data.message) {
                        showAlert('✅ ' + data.message);
                    }
                    
                    setTimeout(() => {
                        dropZone.innerHTML = `
                            <div class="upload-icon">☁️</div>
                            <p class="mb-1">Arrastra aquí tu CSV</p>
                            <small>o haz clic para seleccionar</small>
                        `;
                        dropZone.style.borderColor = '#475569';
                    }, 3000);
                    
                } else {
                    showAlert('❌ Error: ' + (data.message || 'Error desconocido'));
                    resetDropZone();
                }
            } else {
                showAlert('❌ Error al subir el archivo');
                resetDropZone();
            }
        } catch (err) {
            console.error('❌ Error en upload:', err);
            showAlert('❌ Error al subir: ' + err.message);
            resetDropZone();
        }
    }

    function resetDropZone() {
        dropZone.innerHTML = `
            <div class="upload-icon">☁️</div>
            <p class="mb-1">Arrastra aquí tu CSV</p>
            <small>o haz clic para seleccionar</small>
        `;
        dropZone.style.borderColor = '#475569';
    }

    // Drag & Drop
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.add('highlight');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove('highlight');
        });
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.remove('highlight');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            const file = files[0];
            if (!file.name.toLowerCase().endsWith('.csv')) {
                alert('❌ Solo se permiten archivos CSV');
                return;
            }
            if (file.size > 5 * 1024 * 1024) {
                alert('❌ El archivo excede el límite de 5MB');
                return;
            }
            uploadFile(file);
        }
    });

    dropZone.addEventListener('click', (e) => {
        e.preventDefault();
        fileInput.click();
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            const file = e.target.files[0];
            if (!file.name.toLowerCase().endsWith('.csv')) {
                alert('❌ Solo se permiten archivos CSV');
                fileInput.value = '';
                return;
            }
            if (file.size > 5 * 1024 * 1024) {
                alert('❌ El archivo excede el límite de 5MB');
                fileInput.value = '';
                return;
            }
            uploadFile(file);
            fileInput.value = '';
        }
    });

    // ============================================================
    // EVENTOS DE GRÁFICA
    // ============================================================
    document.getElementById('update-chart')?.addEventListener('click', () => {
        renderChart();
    });

    document.getElementById('export-png')?.addEventListener('click', () => {
        exportToPNG();
    });

    // ============================================================
    // CONTROLES DE AGRUPACIÓN (Barra lateral)
    // ============================================================
    const groupMinus = document.getElementById('group-minus');
    const groupPlus = document.getElementById('group-plus');
    const groupReset = document.getElementById('group-reset');

    if (groupMinus) {
        groupMinus.addEventListener('click', () => {
            if (currentGroupIndex > 0) {
                currentGroupIndex--;
                updateGroupControls();
                renderChart();
            }
        });
    }

    if (groupPlus) {
        groupPlus.addEventListener('click', () => {
            if (currentGroupIndex < GROUP_OPTIONS.length - 1) {
                currentGroupIndex++;
                updateGroupControls();
                renderChart();
            }
        });
    }

    if (groupReset) {
        groupReset.addEventListener('click', () => {
            currentGroupIndex = 0;
            updateGroupControls();
            renderChart();
        });
    }

    // ============================================================
    // CONTROLES DE AGRUPACIÓN (En la gráfica)
    // ============================================================
    const groupMinusChart = document.getElementById('group-minus-chart');
    const groupPlusChart = document.getElementById('group-plus-chart');
    const groupResetChart = document.getElementById('group-reset-chart');

    if (groupMinusChart) {
        groupMinusChart.addEventListener('click', () => {
            if (currentGroupIndex > 0) {
                currentGroupIndex--;
                updateGroupControls();
                renderChart();
            }
        });
    }

    if (groupPlusChart) {
        groupPlusChart.addEventListener('click', () => {
            if (currentGroupIndex < GROUP_OPTIONS.length - 1) {
                currentGroupIndex++;
                updateGroupControls();
                renderChart();
            }
        });
    }

    if (groupResetChart) {
        groupResetChart.addEventListener('click', () => {
            currentGroupIndex = 0;
            updateGroupControls();
            renderChart();
        });
    }

    // Inicializar controles
    updateGroupControls();

    // ============================================================
    // VALIDACIÓN EJE Y
    // ============================================================
    const axisY = document.getElementById('axis-y');
    if (axisY) {
        axisY.addEventListener('change', () => {
            const val = axisY.value;
            const option = axisY.querySelector(`option[value="${val}"]`);
            if (option && option.dataset.tipo && option.dataset.tipo !== 'numérico') {
                alert('⚠️ El Eje Y debe ser una columna NUMÉRICA');
                axisY.value = '';
            }
        });
    }

    // ============================================================
    // TEMA OSCURO (CORREGIDO)
    // ============================================================
    function applyTheme(isDark) {
        const toggleBtn = document.getElementById('theme-toggle');
        if (isDark) {
            document.body.classList.add('dark-mode');
            if (toggleBtn) toggleBtn.innerHTML = '☀️ Modo Claro';
            localStorage.setItem('theme', 'dark');
        } else {
            document.body.classList.remove('dark-mode');
            if (toggleBtn) toggleBtn.innerHTML = '🌙 Modo Oscuro';
            localStorage.setItem('theme', 'light');
        }
    }

    function toggleTheme() {
        const isDark = document.body.classList.contains('dark-mode');
        applyTheme(!isDark);
    }

    // Inicializar tema
    const toggleBtn = document.getElementById('theme-toggle');
    if (toggleBtn) {
        // Cargar tema guardado
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'dark') {
            applyTheme(true);
        } else {
            applyTheme(false);
        }
        
        // Evento click
        toggleBtn.addEventListener('click', toggleTheme);
    }

    // ============================================================
    // BOTÓN VER MÁS / VER MENOS
    // ============================================================
    const toggleTableBtn = document.getElementById('toggle-table-btn');
    if (toggleTableBtn) {
        toggleTableBtn.addEventListener('click', () => {
            showFullTable = !showFullTable;
            renderTable();
            toggleTableBtn.innerHTML = showFullTable ? 
                '<i class="bi bi-eye-slash"></i> Ver menos' : 
                '<i class="bi bi-eye"></i> Ver más';
        });
    }

    // ============================================================
    // CARGA INICIAL
    // ============================================================
    loadFileList();

    if (window.currentFilename && window.currentFilename.trim() !== "") {
        console.log('📂 Cargando archivo de sesión:', window.currentFilename);
        loadFileData(window.currentFilename);
    }
});

// ============================================================
// FUNCIÓN: CARGAR LISTA DE ARCHIVOS
// ============================================================
async function loadFileList() {
    try {
        const response = await fetch('/api/list_files');
        const files = await response.json();

        const container = document.getElementById('file-list');
        if (!container) return;
        
        container.innerHTML = '';

        if (files.length === 0) {
            container.innerHTML = '<div class="text-white-50 small">No hay archivos CSV cargados</div>';
            return;
        }

        files.forEach(file => {
            const div = document.createElement('div');
            div.className = 'file-list-item';
            if (file.name === window.currentFilename) {
                div.classList.add('active');
            }
            
            // Nombre del archivo (clic para cargar)
            const nameSpan = document.createElement('span');
            nameSpan.textContent = file.name;
            nameSpan.style.cursor = 'pointer';
            nameSpan.onclick = () => selectFile(file.name);
            
            // Tamaño
            const sizeSpan = document.createElement('small');
            sizeSpan.textContent = file.size + ' KB';
            
            // Botón eliminar
            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'btn btn-danger btn-sm ms-1';
            deleteBtn.style.padding = '2px 6px';
            deleteBtn.style.fontSize = '10px';
            deleteBtn.innerHTML = '<i class="bi bi-trash3"></i>';
            deleteBtn.title = 'Eliminar archivo';
            deleteBtn.onclick = (e) => {
                e.stopPropagation(); // Evitar que se seleccione el archivo
                deleteFile(file.name);
            };
            
            // Contenedor de acciones
            const actionsDiv = document.createElement('div');
            actionsDiv.className = 'd-flex align-items-center gap-1';
            actionsDiv.appendChild(sizeSpan);
            actionsDiv.appendChild(deleteBtn);
            
            div.appendChild(nameSpan);
            div.appendChild(actionsDiv);
            container.appendChild(div);
        });

        // ============================================================
        // EVENTO PARA EL BOTÓN "ELIMINAR TODOS"
        // ============================================================
        const deleteAllBtn = document.getElementById('delete-all-btn');
        if (deleteAllBtn) {
            // Remover eventos anteriores para evitar duplicados
            const newDeleteAllBtn = deleteAllBtn.cloneNode(true);
            deleteAllBtn.parentNode.replaceChild(newDeleteAllBtn, deleteAllBtn);
            newDeleteAllBtn.addEventListener('click', deleteAllFiles);
        }

    } catch (err) {
        console.error('Error cargando lista:', err);
    }
}

// ============================================================
// FUNCIÓN: SELECCIONAR ARCHIVO
// ============================================================
function selectFile(filename) {
    console.log('📂 Seleccionando archivo:', filename);
    window.currentFilename = filename;
    loadFileData(filename);
}

// ============================================================
// FUNCIÓN: CARGAR DATOS DEL ARCHIVO
// ============================================================
async function loadFileData(filename) {
    try {
        console.log('📂 Cargando archivo:', filename);
        const res = await fetch(`/process?file=${encodeURIComponent(filename)}`);
        const data = await res.json();

        if (data.error) {
            showAlert('Error: ' + data.error);
            return;
        }

        console.log('✅ Datos cargados:', data);
        currentFileData = data;

        // ============================================================
        // LLENAR SELECTORES
        // ============================================================
        const selectX = document.getElementById('axis-x');
        const selectY = document.getElementById('axis-y');
        const currentY = selectY ? selectY.value : '';

        if (selectX) {
            selectX.innerHTML = '<option value="">Selecciona...</option>';
        }
        if (selectY) {
            selectY.innerHTML = '<option value="">Selecciona...</option>';
        }

        let firstNumeric = null;
        let firstColumn = null;

        if (data.analisis_columnas) {
            data.analisis_columnas.forEach(col => {
                if (selectX) {
                    const optX = new Option(col.columna, col.columna);
                    optX.dataset.tipo = col.tipo_detectado;
                    selectX.add(optX);
                    if (!firstColumn) firstColumn = col.columna;
                }

                if (col.tipo_detectado === 'numérico' && selectY) {
                    const optY = new Option(col.columna + ' 📊', col.columna);
                    optY.dataset.tipo = col.tipo_detectado;
                    selectY.add(optY);
                    if (!firstNumeric) firstNumeric = col.columna;
                }
            });
        }

        if (selectX && firstColumn) {
            selectX.value = firstColumn;
        }

        if (selectY) {
            if (currentY && selectY.querySelector(`option[value="${currentY}"]`)) {
                selectY.value = currentY;
                console.log(`🔹 Manteniendo Eje Y: ${currentY}`);
            } else if (firstNumeric) {
                selectY.value = firstNumeric;
                console.log(`🔹 Eje Y por defecto: ${firstNumeric}`);
            } else {
                const msg = document.createElement('option');
                msg.value = '';
                msg.textContent = '⚠️ No hay columnas numéricas';
                msg.disabled = true;
                msg.selected = true;
                selectY.add(msg);
            }
        }

        // ============================================================
        // ACTUALIZAR RESUMEN
        // ============================================================
        document.getElementById('summary-name').textContent = data.archivo || '-';
        document.getElementById('summary-rows').textContent = data.total_filas || '-';
        document.getElementById('summary-columns').textContent = data.total_columnas || '-';
        document.getElementById('summary-size').textContent = (data.tamano_kb || '0') + ' KB';
        document.getElementById('summary-delimiter').textContent = data.delimitador || '-';

        // ============================================================
        // GUARDAR DATOS DE TABLA
        // ============================================================
        fullTableData = data.preview_rows || [];
        currentPage = 1;
        showFullTable = false;

        // ============================================================
        // RENDERIZAR TABLA
        // ============================================================
        renderTable();

        const toggleTableBtn = document.getElementById('toggle-table-btn');
        if (toggleTableBtn) {
            toggleTableBtn.innerHTML = '<i class="bi bi-eye"></i> Ver más';
        }

        // ============================================================
        // MOSTRAR GRÁFICA
        // ============================================================
        document.getElementById('chart-placeholder').style.display = 'none';
        document.getElementById('canvas-container').style.display = 'block';

        renderChart();
        loadFileList();

    } catch (err) {
        console.error('❌ Error en loadFileData:', err);
        showAlert('Error cargando archivo: ' + err.message);
    }
}

// ============================================================
// FUNCIÓN: RENDERIZAR TABLA
// ============================================================
function renderTable() {
    const container = document.getElementById('preview-table-container');
    if (!container) return;
    
    const headers = currentFileData?.preview_headers || [];
    const allRows = fullTableData || [];
    
    let rowsToShow = [];
    if (showFullTable) {
        rowsToShow = allRows;
    } else {
        rowsToShow = allRows.slice(0, 10);
    }

    let html = '<div class="table-responsive" style="max-height: 500px; overflow-y: auto;">';
    html += '<table class="table table-sm table-striped table-hover mt-3">';
    
    html += '<thead class="table-dark" style="position: sticky; top: 0; z-index: 10;"><tr>';
    headers.forEach(h => html += `<th>${h}</th>`);
    html += '</tr></thead>';
    
    html += '<tbody>';
    
    if (rowsToShow.length === 0) {
        html += `<tr><td colspan="${headers.length}" class="text-center">No hay datos</td></tr>`;
    } else {
        rowsToShow.forEach(row => {
            html += '<tr>';
            row.forEach(cell => {
                const displayCell = (cell === null || cell === undefined || cell === '') ? '-' : String(cell);
                html += `<td>${displayCell}</td>`;
            });
            html += '</tr>';
        });
    }
    
    if (currentFileData?.averages && currentFileData.averages.length > 0) {
        const hasAvg = currentFileData.averages.some(a => a !== '' && a !== '-' && a !== 0);
        if (hasAvg) {
            html += '<tr class="table-info fw-bold">';
            html += '<td colspan="100%" class="text-center bg-secondary text-white">📊 PROMEDIOS</td>';
            html += '</tr>';
            html += '<tr class="table-info">';
            currentFileData.averages.forEach(avg => {
                const displayAvg = (avg === '' || avg === null || isNaN(avg)) ? '-' : String(avg);
                html += `<td class="fw-bold">${displayAvg}</td>`;
            });
            html += '</tr>';
        }
    }
    
    html += '</tbody></table></div>';

    const totalRows = allRows.length;
    const showing = showFullTable ? totalRows : Math.min(10, totalRows);
    html += `<div class="text-muted small mt-2">Mostrando ${showing} de ${totalRows} filas</div>`;

    container.innerHTML = html;
}

// ============================================================
// FUNCIÓN: RENDERIZAR GRÁFICA
// ============================================================
async function renderChart() {
    const file = window.currentFilename;
    const colX = document.getElementById('axis-x')?.value || '';
    const colY = document.getElementById('axis-y')?.value || '';
    const type = document.getElementById('chart-type')?.value || 'bar';
    const groupSize = currentGroupSize || 1;

    console.log("=" * 60);
    console.log("📊 RENDERIZANDO GRÁFICA");
    console.log("=" * 60);
    console.log(`📂 Archivo: ${file}`);
    console.log(`📌 Eje X: ${colX}`);
    console.log(`📌 Eje Y: ${colY}`);
    console.log(`📌 Tipo: ${type}`);
    console.log(`📌 Group Size: ${groupSize}`);
    console.log("-" * 60);

    if (!file) {
        console.log('⚠️ No hay archivo seleccionado');
        return;
    }

    if (!colY) {
        alert('⚠️ Selecciona una columna NUMÉRICA para el Eje Y');
        return;
    }

    if (currentFileData && currentFileData.analisis_columnas) {
        const colInfo = currentFileData.analisis_columnas.find(c => c.columna === colY);
        if (colInfo && colInfo.tipo_detectado !== 'numérico') {
            alert('⚠️ La columna "' + colY + '" no es numérica');
            return;
        }
    }

    try {
        const res = await fetch(`/chart_data?file=${encodeURIComponent(file)}&column_x=${encodeURIComponent(colX)}&column_y=${encodeURIComponent(colY)}&type=${type}&group_size=${groupSize}`);
        const data = await res.json();

        if (data.error) {
            console.error('❌ Error en gráfica:', data.error);
            showAlert('Error en gráfica: ' + data.error);
            return;
        }

        console.log('📊 Datos de gráfica recibidos:');
        console.log(`   Total datos: ${data.info?.count || 'N/A'}`);
        console.log(`   Min Y: ${data.info?.min_y || 'N/A'}`);
        console.log(`   Max Y: ${data.info?.max_y || 'N/A'}`);
        console.log("=" * 60);

        // ============================================================
        // DETECTAR SI HAY QUE MOSTRAR CONTROLES DE AGRUPACIÓN
        // ============================================================
        const hasManyValues = data.labels && data.labels.length > 20;
        
        let xIsNumeric = false;
        if (currentFileData && currentFileData.analisis_columnas) {
            const colInfo = currentFileData.analisis_columnas.find(c => c.columna === colX);
            if (colInfo && colInfo.tipo_detectado === 'numérico') {
                xIsNumeric = true;
            }
        }
        
        let labelsAreNumeric = true;
        if (data.labels && data.labels.length > 0) {
            for (let i = 0; i < Math.min(10, data.labels.length); i++) {
                if (isNaN(parseFloat(data.labels[i]))) {
                    labelsAreNumeric = false;
                    break;
                }
            }
        }
        
        if ((hasManyValues && xIsNumeric) || (hasManyValues && labelsAreNumeric)) {
            showGroupControls = true;
            console.log('🔹 Activando controles de agrupación (más de 20 valores en X)');
        } else {
            showGroupControls = false;
            if (currentGroupIndex !== 0) {
                currentGroupIndex = 0;
            }
        }
        
        updateGroupControls();

        const canvas = document.getElementById('mainChart');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        if (myChart) {
            myChart.destroy();
            myChart = null;
        }

        const isArea = type === 'area';
        const finalType = isArea ? 'line' : type;

        const chartOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: true },
                title: { 
                    display: true, 
                    text: `📊 ${colY}${colX ? ' por ' + colX : ''}`,
                    font: { size: 14 }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: colY
                    }
                }
            }
        };

        const isCalificacion = colY.toLowerCase().includes('calificacion') || 
                               colY.toLowerCase().includes('calificación');
        if (isCalificacion) {
            console.log('🔹 Calificacion detectada → rango 0-5');
            chartOptions.scales.y.min = 0;
            chartOptions.scales.y.max = 5;
            chartOptions.scales.y.ticks = {
                stepSize: 0.5,
                callback: function(value) {
                    return value % 1 === 0 ? value : value.toFixed(1);
                }
            };
        }

        if (data.labels && data.labels.length > 0 && (finalType === 'bar' || finalType === 'line')) {
            const maxLabelLength = Math.max(...data.labels.map(l => String(l).length));
            if (maxLabelLength > 15 || data.labels.length > 10) {
                chartOptions.scales.x = {
                    ticks: {
                        maxRotation: 90,
                        minRotation: 45,
                        font: { size: 8 }
                    }
                };
            } else if (maxLabelLength > 8) {
                chartOptions.scales.x = {
                    ticks: {
                        maxRotation: 45,
                        minRotation: 20,
                        font: { size: 9 }
                    }
                };
            }
        }

        myChart = new Chart(ctx, {
            type: finalType,
            data: {
                labels: data.labels || [],
                datasets: [{
                    label: colY,
                    data: data.values || [],
                    backgroundColor: isArea ? 'rgba(59, 130, 246, 0.4)' : 
                        (finalType === 'pie' ? getColors(data.values.length) : 'rgba(59, 130, 246, 0.2)'),
                    borderColor: '#2563EB',
                    borderWidth: 2,
                    fill: isArea,
                    tension: 0.3
                }]
            },
            options: chartOptions
        });

        console.log('✅ Gráfica renderizada correctamente');
        updateStats();

    } catch (err) {
        console.error('❌ Error en renderChart:', err);
        showAlert('Error al generar gráfica: ' + err.message);
    }
}

// ============================================================
// FUNCIÓN: ACTUALIZAR ESTADÍSTICAS
// ============================================================
async function updateStats() {
    const file = window.currentFilename;
    const colY = document.getElementById('axis-y')?.value || '';
    const container = document.getElementById('stats-container');

    if (!file || !container) return;

    try {
        const res = await fetch(`/stats?file=${encodeURIComponent(file)}`);
        const data = await res.json();

        if (data.error) {
            container.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
            return;
        }

        if (!colY || !data.estadisticas || !data.estadisticas[colY]) {
            container.innerHTML = `
                <div class="card p-3">
                    <h6 class="fw-bold mb-3">📊 Resumen</h6>
                    <div class="small">
                        <div class="d-flex justify-content-between border-bottom py-1"><span>Total Filas</span><b>${data.total_filas || 0}</b></div>
                        <div class="d-flex justify-content-between border-bottom py-1"><span>Total Columnas</span><b>${data.total_columnas || 0}</b></div>
                        <div class="d-flex justify-content-between py-1"><span>Columnas Numéricas</span><b>${Object.values(data.estadisticas || {}).filter(e => e.tipo === 'numérico').length}</b></div>
                    </div>
                    <hr>
                    <div class="text-muted small">Selecciona una columna numérica para ver estadísticas detalladas</div>
                </div>
            `;
            return;
        }

        const s = data.estadisticas[colY];
        const fmt = (n) => {
            if (n === null || n === undefined || isNaN(n)) return '-';
            return n.toLocaleString('es-ES', { maximumFractionDigits: 2 });
        };

        if (s.tipo === 'texto') {
            container.innerHTML = `
                <div class="card p-3">
                    <h6 class="fw-bold mb-3">📝 ${colY}</h6>
                    <div class="small">
                        <div class="d-flex justify-content-between border-bottom py-1"><span>Total</span><b>${s.total || 0}</b></div>
                        <div class="d-flex justify-content-between border-bottom py-1"><span>Valores Únicos</span><b>${s.valores_unicos || 0}</b></div>
                        <div class="d-flex justify-content-between py-1"><span>Moda</span><b>${s.moda || '-'}</b></div>
                    </div>
                </div>
            `;
            return;
        }

        container.innerHTML = `
            <div class="card p-3" style="max-height: 600px; overflow-y: auto;">
                <h6 class="fw-bold mb-2">📊 ${colY}</h6>
                
                <div class="mb-2 p-2 rounded bg-light">
                    <div class="d-flex justify-content-between small">
                        <span>Datos válidos: <b>${s.no_nulos || 0}</b></span>
                        <span>Nulos: <b>${s.nulos || 0} (${s.porcentaje_nulos || 0}%)</b></span>
                    </div>
                </div>

                <div class="row g-1 mb-2">
                    <div class="col-6"><div class="bg-light p-1 rounded text-center"><small>Media</small><div class="fw-bold">${fmt(s.media)}</div></div></div>
                    <div class="col-6"><div class="bg-light p-1 rounded text-center"><small>Mediana</small><div class="fw-bold">${fmt(s.mediana)}</div></div></div>
                    <div class="col-6"><div class="bg-light p-1 rounded text-center"><small>Moda</small><div class="fw-bold">${fmt(s.moda)}</div></div></div>
                    <div class="col-6"><div class="bg-light p-1 rounded text-center"><small>Rango</small><div class="fw-bold">${fmt(s.rango)}</div></div></div>
                </div>

                <div class="row g-1 mb-2">
                    <div class="col-6"><div class="bg-light p-1 rounded text-center"><small>Mínimo</small><div class="fw-bold">${fmt(s.minimo)}</div></div></div>
                    <div class="col-6"><div class="bg-light p-1 rounded text-center"><small>Máximo</small><div class="fw-bold">${fmt(s.maximo)}</div></div></div>
                    <div class="col-6"><div class="bg-light p-1 rounded text-center"><small>Desv. Estándar</small><div class="fw-bold">${fmt(s.desviacion_estandar)}</div></div></div>
                    <div class="col-6"><div class="bg-light p-1 rounded text-center"><small>Varianza</small><div class="fw-bold">${fmt(s.varianza)}</div></div></div>
                </div>

                <div class="row g-1 mb-2">
                    <div class="col-4"><div class="bg-light p-1 rounded text-center"><small>Q1</small><div class="fw-bold">${fmt(s.q1)}</div></div></div>
                    <div class="col-4"><div class="bg-light p-1 rounded text-center"><small>Q2</small><div class="fw-bold">${fmt(s.q2)}</div></div></div>
                    <div class="col-4"><div class="bg-light p-1 rounded text-center"><small>Q3</small><div class="fw-bold">${fmt(s.q3)}</div></div></div>
                </div>

                <div class="d-flex justify-content-between small">
                    <span>Outliers: <b>${s.outliers || 0}</b></span>
                    <span>Suma: <b>${fmt(s.suma)}</b></span>
                </div>
            </div>
        `;

    } catch (err) {
        console.error('❌ Error en updateStats:', err);
        container.innerHTML = `<div class="alert alert-danger">Error: ${err.message}</div>`;
    }
}

// ============================================================
// FUNCIÓN: COLORES PARA GRÁFICAS
// ============================================================
function getColors(count) {
    const palette = ['#1E3A8A', '#2563EB', '#3B82F6', '#60A5FA', '#93C5FD', '#0EA5E9', '#0284C7', '#38BDF8'];
    return Array.from({ length: count }, (_, i) => palette[i % palette.length]);
}

// ============================================================
// FUNCIÓN: EXPORTAR A PNG
// ============================================================
function exportToPNG() {
    const canvas = document.getElementById('mainChart');
    if (!canvas) {
        alert('No hay gráfica para exportar');
        return;
    }
    const link = document.createElement('a');
    link.download = 'grafica.png';
    link.href = canvas.toDataURL('image/png');
    link.click();
}



// ============================================================
// FUNCIÓN: ELIMINAR UN ARCHIVO
// ============================================================
async function deleteFile(filename) {
    if (!confirm(`¿Estás seguro de que quieres eliminar "${filename}"?`)) {
        return;
    }
    
    try {
        const response = await fetch('/delete_file', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ filename: filename })
        });
        
        const data = await response.json();
        
        if (data.success) {
            console.log('🗑️', data.message);
            showAlert('✅ ' + data.message);
            
            // Si el archivo eliminado era el actual, limpiar UI
            if (window.currentFilename === filename) {
                window.currentFilename = '';
                document.getElementById('stats-container').innerHTML = '';
                document.getElementById('preview-table-container').innerHTML = '';
                document.getElementById('chart-placeholder').style.display = 'block';
                document.getElementById('canvas-container').style.display = 'none';
                document.getElementById('summary-name').textContent = 'Sin archivo';
                document.getElementById('summary-rows').textContent = '-';
                document.getElementById('summary-columns').textContent = '-';
                document.getElementById('summary-size').textContent = '-';
                document.getElementById('summary-delimiter').textContent = '-';
                
                if (myChart) {
                    myChart.destroy();
                    myChart = null;
                }
            }
            
            // Recargar lista de archivos
            await loadFileList();
        } else {
            showAlert('❌ Error: ' + data.message);
        }
    } catch (err) {
        console.error('❌ Error al eliminar:', err);
        showAlert('❌ Error al eliminar: ' + err.message);
    }
}

// ============================================================
// FUNCIÓN: ELIMINAR TODOS LOS ARCHIVOS
// ============================================================
async function deleteAllFiles() {
    const files = document.querySelectorAll('.file-list-item');
    if (files.length === 0) {
        showAlert('No hay archivos para eliminar');
        return;
    }
    
    if (!confirm(`¿Estás seguro de que quieres eliminar TODOS los archivos (${files.length})?`)) {
        return;
    }
    
    try {
        const response = await fetch('/delete_all_files', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            console.log('🗑️', data.message);
            showAlert('✅ ' + data.message);
            
            // Limpiar UI
            window.currentFilename = '';
            document.getElementById('stats-container').innerHTML = '';
            document.getElementById('preview-table-container').innerHTML = '';
            document.getElementById('chart-placeholder').style.display = 'block';
            document.getElementById('canvas-container').style.display = 'none';
            document.getElementById('summary-name').textContent = 'Sin archivo';
            document.getElementById('summary-rows').textContent = '-';
            document.getElementById('summary-columns').textContent = '-';
            document.getElementById('summary-size').textContent = '-';
            document.getElementById('summary-delimiter').textContent = '-';
            
            if (myChart) {
                myChart.destroy();
                myChart = null;
            }
            
            // Recargar lista de archivos
            await loadFileList();
        } else {
            showAlert('❌ Error: ' + data.message);
        }
    } catch (err) {
        console.error('❌ Error al eliminar todos:', err);
        showAlert('❌ Error al eliminar todos: ' + err.message);
    }
}





// ============================================================
// FUNCIÓN: ALERTA
// ============================================================
function showAlert(msg) {
    alert(msg);
}