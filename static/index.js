const API_URL = 'http://127.0.0.1:8000/repairs';

// Global variables
let token = localStorage.getItem('token');
console.log('index.js: Initial token:', token);

let workTypesMetadata = {};
let rooms = [];
let currentRoomIndex = -1;
let focusedInputId = null;
let areaError = false;
let heightError = false;
let isUpdating = false;
let categoryCollapseStates = {};

async function validateToken() {
    if (!token) return false;
    try {
        const response = await fetch(`${API_URL}/me`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        return response.ok;
    } catch (error) {
        console.error('Token validation failed:', error);
        return false;
    }
}

function groupWorkTypesByCategory(workTypes) {
    if (!Array.isArray(workTypes)) {
        console.error('groupWorkTypesByCategory: workTypes is not an array', workTypes);
        return {};
    }
    return workTypes.reduce((acc, work) => {
        const category = work.category || 'Без категории';
        if (!acc[category]) acc[category] = [];
        acc[category].push(work);
        return acc;
    }, {});
}

function getCategoryDisplayName(category) {
    const categoryNames = {
        'полы': 'Полы',
        'стены': 'Стены',
        'потолок': 'Потолок',
        'двери-окна': 'Двери и окна'
    };
    return categoryNames[category] || category;
}

function createArrowIcon() {
    return `
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="6 9 12 15 18 9"></polyline>
        </svg>
    `;
}

document.addEventListener('DOMContentLoaded', async () => {
    console.log('index.js: DOM loaded, token:', token);

    const isTokenValid = await validateToken();
    console.log('index.js: Token valid:', isTokenValid);
    if (!isTokenValid) {
        token = null;
        localStorage.removeItem('token');
    }
    window.token = token;

    const loginEvent = new Event('userLoggedIn');
    document.dispatchEvent(loginEvent);

    addRoom('Комната 1');
    await populateWorkTypesTable();

    // Ensure header is fully loaded before proceeding
    const header = document.getElementById('header');
    if (header && typeof window.updateTabVisibility === 'function') {
        window.updateTabVisibility();
    }
});

function addRoom(name) {
    const room = { name, area: "", height: "", workTypes: {} };
    rooms.push(room);
    currentRoomIndex = rooms.length - 1;
    updateRoomDisplay();
}

function updateRoomDisplay() {
    if (isUpdating) return;
    isUpdating = true;

    const roomSelection = document.getElementById('room-selection');
    roomSelection.innerHTML = '';

    rooms.forEach((room, index) => {
        const roomCard = document.createElement('div');
        roomCard.classList.add('room-card');
        if (index === currentRoomIndex) roomCard.classList.add('current');
        roomCard.innerHTML = `
            <label>Комната:</label>
            <input type="text" id="room-name-${index}" value="${room.name}" onfocus="this.select(); focusedInputId = this.id;" oninput="updateRoomName(${index}, this.value)">
            <div>
                <label>Площадь, м²</label>
                <input type="text" id="room-area-${index}" pattern="[0-9]*\.?[0-9]+" value="${room.area}" placeholder="0" onfocus="this.select(); focusedInputId = this.id; setActiveRoom(${index}); clearAreaError();" onwheel="return false;" class="${areaError && index === currentRoomIndex && !room.area ? 'error-border' : ''}">
            </div>
            <div>
                <label>Высота, м</label>
                <input type="text" id="room-height-${index}" pattern="[0-9]*\.?[0-9]+" value="${room.height}" placeholder="0" onfocus="this.select(); focusedInputId = this.id; setActiveRoom(${index}); clearHeightError();" onwheel="return false;" class="${heightError && index === currentRoomIndex && !room.height ? 'error-border' : ''}">
            </div>
        `;
        roomCard.addEventListener('click', (e) => {
            if (e.target.tagName !== 'INPUT') {
                currentRoomIndex = index;
                updateRoomDisplay();
            }
        });
        roomSelection.appendChild(roomCard);

        const areaInput = document.getElementById(`room-area-${index}`);
        const heightInput = document.getElementById(`room-height-${index}`);
        areaInput.addEventListener('input', (e) => {
            const value = e.target.value.replace(/[^0-9.]/g, '');
            e.target.value = value;
            updateCurrentRoom(index);
        });
        heightInput.addEventListener('input', (e) => {
            const value = e.target.value.replace(/[^0-9.]/g, '');
            e.target.value = value;
            updateCurrentRoom(index);
        });
    });

    const addButton = document.createElement('button');
    addButton.classList.add('add-room-btn');
    addButton.id = 'add-room-btn';
    addButton.textContent = '+';
    addButton.addEventListener('click', () => {
        const newRoomNumber = rooms.length + 1;
        addRoom(`Комната ${newRoomNumber}`);
    });
    roomSelection.appendChild(addButton);

    if (focusedInputId) {
        const inputToFocus = document.getElementById(focusedInputId);
        if (inputToFocus) {
            inputToFocus.focus();
            inputToFocus.select();
        }
        focusedInputId = null;
    }

    populateWorkTypesTable();
    isUpdating = false;
}

function setActiveRoom(index) {
    if (index !== currentRoomIndex) {
        currentRoomIndex = index;
        updateRoomDisplay();
    }
}

function updateRoomName(index, newName) {
    if (index >= 0 && index < rooms.length) rooms[index].name = newName;
}

function updateCurrentRoom(index) {
    if (index >= 0 && index < rooms.length) {
        const room = rooms[index];
        const areaInput = document.getElementById(`room-area-${index}`);
        const heightInput = document.getElementById(`room-height-${index}`);
        room.area = areaInput.value;
        room.height = heightInput.value;
        areaInput.value = room.area;
        heightInput.value = room.height;
    }
}

function clearAreaError() { areaError = false; updateRoomDisplay(); }
function clearHeightError() { heightError = false; updateRoomDisplay(); }

async function populateWorkTypesTable() {
    const tableBody = document.getElementById('workTypesTableBody');
    const totalCostContainer = document.getElementById('total-cost-container');
    if (tableBody) tableBody.innerHTML = '<tr><td colspan="4">Загрузка типов работ...</td>';

    try {
        const response = await fetch(`${API_URL}/work_types`);
        if (!response.ok) throw new Error(`Не удалось загрузить типы работ: ${response.status} - ${response.statusText}`);
        const workTypes = await response.json();
        console.log('Work types:', workTypes);

        if (tableBody) {
            const scrollPosition = window.scrollY;
            const groupedWorkTypes = groupWorkTypesByCategory(workTypes);
            tableBody.innerHTML = '';

            let categoryIndex = 0;
            Object.keys(groupedWorkTypes).forEach(category => {
                const displayName = getCategoryDisplayName(category);
                const works = groupedWorkTypes[category];

                const categoryRow = document.createElement('tr');
                const categoryCell = document.createElement('td');
                categoryCell.colSpan = 4;
                categoryCell.className = 'category-header';
                categoryCell.style.setProperty('--category-index', categoryIndex);
                categoryCell.innerHTML = `<div class="category-header-content">${createArrowIcon()} ${displayName}</div>`;
                categoryRow.appendChild(categoryCell);
                tableBody.appendChild(categoryRow);

                categoryIndex++;

                if (categoryCollapseStates[category] === undefined) categoryCollapseStates[category] = true;
                const isCollapsed = categoryCollapseStates[category];
                if (isCollapsed) categoryCell.classList.add('collapsed');

                const workRows = works.map(workType => {
                    workTypesMetadata[workType.id] = {
                        labor_cost_per_unit: workType.labor_cost_per_unit,
                        complexity_factor: workType.complexity_factor,
                        unit: workType.unit,
                        category: workType.category,
                        name: workType.name,
                        material_consumption: workType.material_consumption || 0,
                        material_cost_per_unit: workType.material_cost_per_unit || 0
                    };

                    const row = document.createElement('tr');
                    row.className = 'work-row';
                    row.setAttribute('data-category', category);
                    if (isCollapsed) row.classList.add('hidden');
                    const savedVolume = currentRoomIndex >= 0 && rooms[currentRoomIndex].workTypes[workType.id] !== undefined ?
                        rooms[currentRoomIndex].workTypes[workType.id] : '';
                    row.innerHTML = `
                        <td>${workType.name}</td>
                        <td class="price-per-unit">${workType.labor_cost_per_unit} руб/${workType.unit}</td>
                        <td class="volume">
                            <input type="text" pattern="[0-9]*\.?[0-9]+" class="work-type-volume" 
                                   data-work-type-id="${workType.id}" 
                                   value="${savedVolume}" 
                                   placeholder="${workType.unit}" 
                                   onfocus="this.select()" 
                                   onblur="updateVolume(this)" 
                                   onwheel="return false;">
                            <button type="button" class="apply-volume-btn">По комнате</button>
                        </td>
                        <td class="cost" id="cost-${workType.id}">-</td>
                    `;
                    return row;
                });

                workRows.forEach(row => tableBody.appendChild(row));

                categoryCell.addEventListener('click', () => {
                    const isCollapsed = categoryCell.classList.toggle('collapsed');
                    categoryCollapseStates[category] = isCollapsed;
                    workRows.forEach(row => row.classList.toggle('hidden', isCollapsed));
                });

                workRows.forEach(row => {
                    const workTypeId = parseInt(row.querySelector('.work-type-volume').dataset.workTypeId);
                    const volumeInput = row.querySelector('.work-type-volume');
                    const volume = parseFloat(volumeInput.value) || 0;
                    const costCell = row.querySelector(`#cost-${workTypeId}`);
                    if (volume > 0) {
                        updateCostDisplay(costCell, workTypeId, volume);
                    }

                    const applyButton = row.querySelector('.apply-volume-btn');
                    applyButton.addEventListener('click', () => {
                        if (currentRoomIndex < 0) {
                            alert('Пожалуйста, добавьте комнату.');
                            return;
                        }
                        const currentRoom = rooms[currentRoomIndex];
                        areaError = !currentRoom.area;
                        heightError = !currentRoom.height;
                        if (areaError || heightError) {
                            updateRoomDisplay();
                            return;
                        }

                        const area = parseFloat(currentRoom.area);
                        const height = parseFloat(currentRoom.height);
                        let wallArea = 0.0, floorArea = 0.0, perimeter = 0.0;
                        if (area > 0 && height > 0) {
                            const side = Math.sqrt(area);
                            perimeter = 4 * side;
                            floorArea = area;
                            wallArea = perimeter * height;
                        }

                        let calculatedVolume = 0;
                        const workTypeName = workTypesMetadata[workTypeId].name.toLowerCase();
                        const workTypeCategory = workTypesMetadata[workTypeId].category.toLowerCase();
                        if (workTypeName.includes('стен') || workTypeName.includes('обои')) {
                            calculatedVolume = wallArea;
                        } else if (workTypeName.includes('угол') || workTypeName.includes('плинтус') || workTypeName.includes('бордюр') || workTypeName.includes('багет')) {
                            calculatedVolume = perimeter;
                        } else if (workTypeCategory.includes('пол') || workTypeName.includes('пол') || workTypeName.includes('потолок')) {
                            calculatedVolume = floorArea;
                        } else {
                            calculatedVolume = floorArea;
                        }

                        volumeInput.value = calculatedVolume.toFixed(2);
                        rooms[currentRoomIndex].workTypes[workTypeId] = parseFloat(calculatedVolume.toFixed(2));
                        updateVolume(volumeInput); // Call updateVolume to process the new value
                    });
                });
            });

            window.scrollTo(0, scrollPosition);
            updateTotalCost(); // Ensure total cost is updated after table population
        }
    } catch (error) {
        console.error('Ошибка загрузки типов работ:', error);
        if (tableBody) tableBody.innerHTML = '<tr><td colspan="4">Не удалось загрузить типы работ. Проверьте подключение к серверу или обратитесь в поддержку.</td></tr>';
    }
}

function updateVolume(input) {
    const workTypeId = parseInt(input.dataset.workTypeId);
    let value = input.value.replace(/[^0-9.]/g, '');
    const parts = value.split('.');
    if (parts.length > 2) value = parts[0] + '.' + parts.slice(1).join('');
    const volume = parseFloat(value);

    if (currentRoomIndex >= 0) {
        // Only set volume and update cost if a valid number is entered
        if (!isNaN(volume) && volume > 0) {
            rooms[currentRoomIndex].workTypes[workTypeId] = volume;
            input.value = volume.toFixed(2);
        } else {
            // Clear the volume and cost if no valid volume is entered
            delete rooms[currentRoomIndex].workTypes[workTypeId];
            input.value = ''; // Clear the input field
        }
        const costCell = document.querySelector(`#cost-${workTypeId}`);
        if (costCell) {
            updateCostDisplay(costCell, workTypeId, volume);
        }
        updateTotalCost();
    }
}

function updateCostDisplay(costCell, workTypeId, volume) {
    if (!volume || isNaN(volume) || volume <= 0) {
        costCell.innerHTML = '-'; // Display "-" instead of "0.00" when no valid volume
        return;
    }

    const { labor_cost_per_unit, complexity_factor, material_consumption, material_cost_per_unit } = workTypesMetadata[workTypeId];
    const laborCost = volume * labor_cost_per_unit * complexity_factor;
    const materialCost = volume * material_consumption * material_cost_per_unit;
    const totalCost = laborCost + materialCost;

    costCell.innerHTML = `
        <div class="cost-breakdown">
            Работа: ${laborCost.toFixed(2)} + Материалы: ${materialCost.toFixed(2)} = ${totalCost.toFixed(2)}
        </div>
    `;
}

function updateTotalCost() {
    const workTypeInputs = document.querySelectorAll('.work-type-volume');
    let totalLaborCost = 0;
    let totalMaterialCost = 0;

    if (currentRoomIndex < 0) {
        document.getElementById('total-cost').textContent = '0.00 руб';
        document.getElementById('total-labor-cost').textContent = '0.00 руб';
        document.getElementById('total-material-cost').textContent = '0.00 руб';
        return;
    }

    workTypeInputs.forEach(input => {
        const workTypeId = parseInt(input.dataset.workTypeId);
        const volume = currentRoomIndex >= 0 ? (rooms[currentRoomIndex].workTypes[workTypeId] || 0) : 0;
        if (volume > 0 && workTypesMetadata[workTypeId]) {
            const { labor_cost_per_unit, complexity_factor, material_consumption, material_cost_per_unit } = workTypesMetadata[workTypeId];

            // Calculate labor cost
            const laborCost = volume * labor_cost_per_unit * complexity_factor;
            totalLaborCost += laborCost;

            // Calculate material cost using backend-provided material_cost_per_unit
            const materialConsumption = parseFloat(material_consumption) || 0;
            const materialCost = volume * materialConsumption * material_cost_per_unit;
            totalMaterialCost += materialCost;
        }
    });

    const totalCost = totalLaborCost + totalMaterialCost;
    const totalCostContainer = document.getElementById('total-cost-container');
    if (totalCostContainer) {
        const existingButton = document.getElementById('save-button');
        if (existingButton) existingButton.remove();
        document.getElementById('total-cost').textContent = `${totalCost.toFixed(2)} руб`;
        document.getElementById('total-labor-cost').textContent = `${totalLaborCost.toFixed(2)} руб`;
        document.getElementById('total-material-cost').textContent = `${totalMaterialCost.toFixed(2)} руб`;

        const saveButton = document.createElement('button');
        saveButton.id = 'save-button';
        saveButton.textContent = 'Сохранить';
        saveButton.style.padding = '5px 10px';
        saveButton.style.backgroundColor = '#4b5563';
        saveButton.style.color = 'white';
        saveButton.style.border = 'none';
        saveButton.style.borderRadius = '4px';
        saveButton.style.fontSize = '14px';
        saveButton.style.cursor = 'pointer';
        saveButton.addEventListener('click', async () => {
            if (await validateToken()) {
                const workTypesData = Array.from(document.querySelectorAll('.work-type-volume')).map(input => ({
                    id: parseInt(input.dataset.workTypeId),
                    volume: parseFloat(input.value) || 0,
                    name: workTypesMetadata[parseInt(input.dataset.workTypeId)].name,
                    unit: workTypesMetadata[parseInt(input.dataset.workTypeId)].unit
                })).filter(wt => wt.volume > 0);
                const payload = {
                    area: parseFloat(rooms[currentRoomIndex]?.area) || null,
                    height: parseFloat(rooms[currentRoomIndex]?.height) || null,
                    work_types: workTypesData
                };
                try {
                    const response = await fetch(`${API_URL}/estimates`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}`
                        },
                        body: JSON.stringify(payload)
                    });
                    if (!response.ok) throw new Error('Failed to save estimate');
                    alert('Таблица сохранена в личный кабинет!');
                } catch (error) {
                    console.error('Save error:', error);
                    alert('Ошибка при сохранении: ' + error.message);
                }
            } else {
                window.showLoginModal();
            }
        });
        totalCostContainer.appendChild(saveButton);

        saveButton.addEventListener('mouseover', () => saveButton.style.backgroundColor = '#6b7280');
        saveButton.addEventListener('mouseout', () => saveButton.style.backgroundColor = '#4b5563');
    }
}

function displayResult(result) {
    const resultDiv = document.getElementById('result');
    if (resultDiv) {
        resultDiv.innerHTML = `
            <div class="breakdown">
                <p><strong>Общая стоимость:</strong> ${Math.round(result.total_cost)} руб</p>
                <p><strong>Стоимость труда:</strong> ${Math.round(result.total_labor_cost)} руб</p>
                <p><strong>Стоимость материалов:</strong> ${Math.round(result.total_material_cost || 0)} руб</p>
            </div>
            <ul>
                ${result.work_types.map(wt => `
                    <li>${wt.name}: ${(wt.units || 0).toFixed(2)} ${wt.unit || ''}, Труд: ${Math.round(wt.labor_cost || 0)} руб, Материалы: ${Math.round(wt.material_cost || 0)} руб</li>
                `).join('')}
            </ul>
        `;
    }
}

// Modal functionality
window.showLoginModal = function() {
    const loginModal = document.getElementById('loginModal');
    if (!loginModal) return;
    loginModal.removeAttribute('aria-hidden');
    loginModal.style.display = 'flex';
    setTimeout(() => document.getElementById('loginEmail')?.focus(), 100);

    document.getElementById('loginForm').style.display = 'block';
    document.getElementById('registerForm').style.display = 'none';
    document.getElementById('loginError').style.display = 'none';
    document.getElementById('registerError').style.display = 'none';
    document.getElementById('loginTabButton').classList.add('active');
    document.getElementById('registerTabButton').classList.remove('active');
};

document.getElementById('loginTabButton')?.addEventListener('click', () => {
    document.getElementById('loginForm').style.display = 'block';
    document.getElementById('registerForm').style.display = 'none';
    document.getElementById('loginTabButton').classList.add('active');
    document.getElementById('registerTabButton').classList.remove('active');
    document.getElementById('loginError').style.display = 'none';
    document.getElementById('registerError').style.display = 'none';
});

document.getElementById('registerTabButton')?.addEventListener('click', () => {
    document.getElementById('loginForm').style.display = 'none';
    document.getElementById('registerForm').style.display = 'block';
    document.getElementById('loginTabButton').classList.remove('active');
    document.getElementById('registerTabButton').classList.add('active');
    document.getElementById('loginError').style.display = 'none';
    document.getElementById('registerError').style.display = 'none';
});

document.getElementById('cancelLogin')?.addEventListener('click', () => {
    document.getElementById('loginModal').style.display = 'none';
    document.getElementById('loginModal').setAttribute('aria-hidden', 'true');
    document.getElementById('loginError').style.display = 'none';
    document.getElementById('registerError').style.display = 'none';
});

document.getElementById('cancelRegister')?.addEventListener('click', () => {
    document.getElementById('loginModal').style.display = 'none';
    document.getElementById('loginModal').setAttribute('aria-hidden', 'true');
    document.getElementById('loginError').style.display = 'none';
    document.getElementById('registerError').style.display = 'none';
});

document.getElementById('loginForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;

    try {
        const response = await fetch(`${API_URL}/token`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ email, password })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP ${response.status}: ${JSON.stringify(errorData)}`);
        }

        const data = await response.json();
        window.token = data.access_token;
        localStorage.setItem('token', window.token);
        console.log('index.js: Login successful, token set:', window.token);
        document.getElementById('loginModal').style.display = 'none';
        document.getElementById('loginModal').setAttribute('aria-hidden', 'true');

        const loginEvent = new Event('userLoggedIn');
        document.dispatchEvent(loginEvent);

        setTimeout(() => window.location.href = '/static/cabinet.html', 100);
    } catch (error) {
        document.getElementById('loginError').textContent = error.message;
        document.getElementById('loginError').style.display = 'block';
    }
});

document.getElementById('registerForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('registerName').value;
    const email = document.getElementById('registerEmail').value;
    const password = document.getElementById('registerPassword').value;

    try {
        const response = await fetch(`${API_URL}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, password })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Registration failed');
        }

        document.getElementById('loginModal').style.display = 'none';
        document.getElementById('loginModal').setAttribute('aria-hidden', 'true');
        alert('Регистрация прошла успешно! Пожалуйста, войдите.');
        document.getElementById('loginForm').style.display = 'block';
        document.getElementById('registerForm').style.display = 'none';
        document.getElementById('loginTabButton').classList.add('active');
        document.getElementById('registerTabButton').classList.remove('active');
    } catch (error) {
        document.getElementById('registerError').textContent = error.message;
        document.getElementById('registerError').style.display = 'block';
    }
});

document.getElementById('estimateForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const workTypeInputs = document.querySelectorAll('.work-type-volume');
    const workTypesData = Array.from(workTypeInputs).map(input => ({
        id: parseInt(input.dataset.workTypeId),
        volume: parseFloat(input.value) || 0
    })).filter(wt => wt.volume > 0);

    if (workTypesData.length === 0) {
        document.getElementById('result').innerHTML = '<p class="error">Пожалуйста, введите объем хотя бы для одного типа работы.</p>';
        return;
    }

    const payload = { work_types: workTypesData };
    const area = parseFloat(document.getElementById(`room-area-${currentRoomIndex}`).value) || null;
    const height = parseFloat(document.getElementById(`room-height-${currentRoomIndex}`).value) || null;
    if (area && height) {
        payload.area = area;
        payload.height = height;
    }

    console.log('Sending payload to /calculate_estimate:', payload);

    try {
        const response = await fetch(`${API_URL}/calculate_estimate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...(window.token ? { 'Authorization': `Bearer ${window.token}` } : {})
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }

        const result = await response.json();
        displayResult(result);

        if (window.token) {
            const saveResponse = await fetch(`${API_URL}/estimates`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${window.token}`
                },
                body: JSON.stringify(payload)
            });

            if (!saveResponse.ok) {
                const errorData = await saveResponse.json();
                console.error('Failed to save estimate:', errorData.detail);
                throw new Error(`Failed to save estimate: ${errorData.detail}`);
            }
            console.log('Estimate saved successfully');
        }
    } catch (error) {
        document.getElementById('result').innerHTML = `<p class="error">Ошибка: ${error.message}</p>`;
    }
});