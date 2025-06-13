window.token = localStorage.getItem('token');
console.log('cabinet.js: Initialized window.token from localStorage:', window.token);

document.addEventListener('DOMContentLoaded', async () => {
    console.log('cabinet.js: DOM loaded, token:', window.token);

    // Let header.js handle token validation and redirect if invalid
    if (!window.token) {
        console.log('cabinet.js: No token found, redirecting to login');
        window.location.href = '/static/index.html';
        return;
    }

    await loadEstimates();
});

async function loadEstimates() {
    try {
        const response = await fetch('http://localhost:8000/repairs/my_estimates', {
            headers: {
                'Authorization': `Bearer ${window.token}`
            }
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(errorText || 'Failed to load estimates');
        }

        const estimates = await response.json();
        console.log('cabinet.js: Estimates loaded:', estimates);
        renderEstimates(estimates);
    } catch (error) {
        console.error('cabinet.js: Ошибка загрузки смет:', error);
        // Redirect to login on 401 Unauthorized
        if (error.message.includes('Could not validate credentials')) {
            console.log('cabinet.js: Unauthorized, redirecting to login');
            localStorage.removeItem('token');
            window.token = null;
            window.location.href = '/static/index.html';
        }
    }
}

function renderEstimates(estimates) {
    const tableBody = document.getElementById('estimatesTableBody');
    if (!tableBody) {
        console.error('cabinet.js: Table body element not found');
        return;
    }

    tableBody.innerHTML = '';

    if (estimates.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="4">Нет сохранённых смет</td></tr>';
        return;
    }

    estimates.forEach(estimate => {
        // Main row for the estimate
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${estimate.id}</td>
            <td>${new Date(estimate.created_at).toLocaleDateString()}</td>
            <td>${estimate.total_cost.toFixed(2)}</td>
            <td>
                <button onclick="viewEstimateDetails(${estimate.id}, this)">Подробнее</button>
            </td>
        `;
        row.dataset.estimateId = estimate.id; // Store estimate ID for reference
        tableBody.appendChild(row);

        // Details row (hidden by default)
        const detailsRow = document.createElement('tr');
        detailsRow.classList.add('details-row');
        detailsRow.id = `details-${estimate.id}`;
        const detailsCell = document.createElement('td');
        detailsCell.colSpan = 4; // Span across all columns
        detailsCell.innerHTML = `
            <div>
                <p><strong>ID:</strong> ${estimate.id}</p>
                <p><strong>Дата создания:</strong> ${new Date(estimate.created_at).toLocaleString()}</p>
                <p><strong>Помещение:</strong> Площадь: ${estimate.premise.area.toFixed(2)} м², Высота: ${estimate.premise.height.toFixed(2)} м</p>
                <p><strong>Общая стоимость:</strong> ${estimate.total_cost.toFixed(2)} руб.</p>
                <p><strong>Стоимость работ:</strong> ${estimate.total_labor_cost.toFixed(2)} руб.</p>
                <p><strong>Стоимость материалов:</strong> ${estimate.total_material_cost.toFixed(2)} руб.</p>
                <h3>Работы:</h3>
                <table border="1">
                    <thead>
                        <tr>
                            <th>Название</th>
                            <th>Объём</th>
                            <th>Единица</th>
                            <th>Стоимость работ</th>
                            <th>Стоимость материалов</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${estimate.work_types.map(wt => `
                            <tr>
                                <td>${wt.name}</td>
                                <td>${wt.units.toFixed(2)}</td>
                                <td>${wt.unit}</td>
                                <td>${wt.labor_cost.toFixed(2)} руб.</td>
                                <td>${wt.material_cost.toFixed(2)} руб.</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
        detailsRow.appendChild(detailsCell);
        tableBody.appendChild(detailsRow);
    });
}

function viewEstimateDetails(estimateId, button) {
    const detailsRow = document.getElementById(`details-${estimateId}`);
    if (!detailsRow) {
        console.error('cabinet.js: Details row not found for estimate:', estimateId);
        return;
    }

    // Toggle visibility
    const isVisible = detailsRow.style.display === 'table-row';
    detailsRow.style.display = isVisible ? 'none' : 'table-row';

    // Update button text
    button.textContent = isVisible ? 'Подробнее' : 'Скрыть';
}