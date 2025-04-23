document.addEventListener('DOMContentLoaded', function() {
    const calculateGhpBtn = document.getElementById('calculate-ghp');
    const mrpTablesContainer = document.getElementById('mrp-tables');
    let currentProduction = [];
    let currentPeriods = [];
    let componentsData = {};

    calculateGhpBtn.addEventListener('click', calculateGHP);

    function calculateGHP() {
        const periods = Array.from(document.querySelectorAll('#ghp-table th:not(:first-child)'))
                         .map(th => parseInt(th.textContent));
        const demand = Array.from(document.querySelectorAll('#ghp-table .demand-input'))
                         .slice(0, periods.length)
                         .map(input => Math.max(0, parseInt(input.value) || 0));
        
        const leadTime = Math.max(0, parseInt(document.getElementById('lead-time').value) || 0);
        const inventory = Math.max(0, parseInt(document.getElementById('inventory').value) || 0);

        fetch('/calculate_ghp', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                periods: periods,
                demand: demand,
                lead_time: leadTime,
                inventory: inventory
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) throw new Error(data.error);
            
            currentPeriods = data.periods || periods;
            currentProduction = data.production || [];
            componentsData = data.components || {};
            
            // Update GHP table
            document.getElementById('available-row').style.display = '';
            document.getElementById('production-row').style.display = '';
            
            data.available.forEach((value, index) => {
                const cell = document.querySelector(`.available[data-period="${index}"]`);
                if (cell) cell.textContent = value;
            });
            
            data.production.forEach((value, index) => {
                const cell = document.querySelector(`.production[data-period="${index}"]`);
                if (cell) cell.textContent = value;
            });
            
            // Load MRP tables
            loadMRPTables();
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Wystąpił błąd: ' + error.message);
        });
    }

    function loadMRPTables() {
        mrpTablesContainer.innerHTML = '';
        mrpTablesContainer.style.display = 'block';
        
        for (const [componentId, component] of Object.entries(componentsData)) {
            createMRPTable(componentId, component);
        }
    }

    function createMRPTable(componentId, component) {
        const demand = currentProduction.map(p => p * (component.multiplier || 1));
        const tableHtml = `
        <div class="table-container" data-component="${componentId}">
            <h3 class="table-title">${component.name} (BOM Level: ${component.bom_level})</h3>
            <div class="table-controls">
                <label>
                    Czas realizacji:
                    <input type="number" class="lead-time" min="0" value="${component.lead_time}">
                </label>
                <label>
                    Wielkość partii:
                    <input type="number" class="lot-size" min="1" value="${component.lot_size}">
                </label>
                <label>
                    Na stanie:
                    <input type="number" class="inventory" min="0" value="${component.initial_inventory}">
                </label>
                <button class="recalculate-btn">Przelicz MRP</button>
            </div>
            <table class="table">
                <thead>
                    <tr>
                        <th>Okres</th>
                        ${currentPeriods.map(p => `<th>${p}</th>`).join('')}
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Całkowite zapotrzebowanie</td>
                        ${currentPeriods.map((p, i) => `<td class="demand" data-period="${i}">${demand[i] || 0}</td>`).join('')}
                    </tr>
                    <tr>
                        <td>Planowane przyjęcia</td>
                        ${currentPeriods.map((p, i) => `
                        <td>
                            <input type="number" class="planned-receipt" data-period="${i}" min="0" value="0">
                        </td>`).join('')}
                    </tr>
                    <tr>
                        <td>Przewidywane na stanie</td>
                        ${currentPeriods.map((p, i) => `<td class="projected-on-hand" data-period="${i}">0</td>`).join('')}
                    </tr>
                    <tr>
                        <td>Zapotrzebowanie netto</td>
                        ${currentPeriods.map((p, i) => `<td class="net-requirements" data-period="${i}">0</td>`).join('')}
                    </tr>
                    <tr>
                        <td>Planowane zamówienia</td>
                        ${currentPeriods.map((p, i) => `<td class="planned-orders" data-period="${i}">0</td>`).join('')}
                    </tr>
                    <tr>
                        <td>Planowane przyjęcie zamówień</td>
                        ${currentPeriods.map((p, i) => `<td class="planned-order-receipts" data-period="${i}">0</td>`).join('')}
                    </tr>
                </tbody>
            </table>
        </div>`;
        
        mrpTablesContainer.insertAdjacentHTML('beforeend', tableHtml);
        setupMRPTableListeners(componentId);
        calculateMRP(componentId);
    }

    function setupMRPTableListeners(componentId) {
        const container = document.querySelector(`.table-container[data-component="${componentId}"]`);
        
        container.querySelector('.recalculate-btn').addEventListener('click', () => {
            calculateMRP(componentId);
        });
        
        container.querySelector('.lead-time').addEventListener('change', () => {
            calculateMRP(componentId);
        });
        
        container.querySelector('.lot-size').addEventListener('change', () => {
            calculateMRP(componentId);
        });
        
        container.querySelector('.inventory').addEventListener('change', () => {
            calculateMRP(componentId);
        });
        
        container.querySelectorAll('.planned-receipt').forEach(input => {
            input.addEventListener('change', () => {
                calculateMRP(componentId);
            });
        });
    }

    function calculateMRP(componentId) {
        const container = document.querySelector(`.table-container[data-component="${componentId}"]`);
        if (!container) return;
        
        const demand = Array.from(container.querySelectorAll('.demand'))
                         .slice(0, currentPeriods.length)
                         .map(td => parseInt(td.textContent) || 0);
        const leadTime = Math.max(0, parseInt(container.querySelector('.lead-time').value) || 0);
        const lotSize = Math.max(1, parseInt(container.querySelector('.lot-size').value) || 1);
        const inventory = Math.max(0, parseInt(container.querySelector('.inventory').value) || 0);
        const manualReceipts = Array.from(container.querySelectorAll('.planned-receipt'))
                                 .slice(0, currentPeriods.length)
                                 .map(input => parseInt(input.value) || 0);
        
        fetch('/calculate_mrp', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                periods: currentPeriods,
                demand: demand,
                lead_time: leadTime,
                lot_size: lotSize,
                inventory: inventory,
                manual_receipts: manualReceipts
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) throw new Error(data.error);
            
            // Update table with calculated data
            data.projected_on_hand.forEach((value, index) => {
                const cell = container.querySelector(`.projected-on-hand[data-period="${index}"]`);
                if (cell) cell.textContent = value;
            });
            
            data.net_requirements.forEach((value, index) => {
                const cell = container.querySelector(`.net-requirements[data-period="${index}"]`);
                if (cell) cell.textContent = value;
            });
            
            data.planned_orders.forEach((value, index) => {
                const cell = container.querySelector(`.planned-orders[data-period="${index}"]`);
                if (cell) cell.textContent = value;
            });
            
            data.planned_order_receipts.forEach((value, index) => {
                const cell = container.querySelector(`.planned-order-receipts[data-period="${index}"]`);
                if (cell) cell.textContent = value;
            });
            
            // Update planned receipts with manual entries + order receipts
            data.manual_receipts.forEach((value, index) => {
                const input = container.querySelector(`.planned-receipt[data-period="${index}"]`);
                if (input) input.value = value;
            });
                // Automatyczne uzupełnienie planned-receipt wartościami z planned-order-receipts
    data.planned_order_receipts.forEach((value, index) => {
        const input = container.querySelector(`.planned-receipt[data-period="${index}"]`);
        if (input) input.value = value;
    });
        })
        .catch(error => {
            console.error('Error calculating MRP:', error);
        });
    }
});