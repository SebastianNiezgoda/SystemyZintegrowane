from flask import Flask, render_template, request, redirect, url_for, jsonify
from collections import defaultdict

app = Flask(__name__)

# Inicjalizacja danych
initial_data = {
    'initial_stock': {},
    'ghp_table': {
        'weeks': [f'Week {i+1}' for i in range(8)],
        'rows': {
            'Przewidywany popyt': [0] * 8,
            'Produkcja': [0] * 8,
            'Aktualny stan': [0] * 8
        }
    },
    'bom': {
        'Łóżko': {'time': 1, 'components': {'Zagłówek': 1, 'Stelaż': 1, 'Rama łóżka': 1}},
        'Stelaż': {'time': 1, 'components': {'Belka wzmacniająca': 1, 'Listwy sprężynujące': 8}},
        'Rama łóżka': {'time': 1, 'components': {'Belki ramy': 4, 'Nogi': 4}},
        'Zagłówek': {'time': 2},
        'Belka wzmacniająca': {'time': 1},
        'Listwy sprężynujące': {'time': 1},
        'Belki ramy': {'time': 1},
        'Nogi': {'time': 2}
    },
    'batch_sizes': {},
    'mrp_tables': {}
}

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        initial_data['initial_stock']['Łóżko'] = int(request.form['initial_stock_product'])
        initial_data['batch_sizes']['Łóżko'] = int(request.form['batch_size_Łóżko'])
        
        for part in initial_data['bom']:
            if part != 'Łóżko':
                initial_data['initial_stock'][part] = int(request.form[f'initial_stock_{part}'])
                initial_data['batch_sizes'][part] = int(request.form[f'batch_size_{part}'])
        
        initial_data['ghp_table']['rows']['Przewidywany popyt'] = [
            int(request.form[f'demand_week_{i+1}']) for i in range(8)
        ]
        return redirect(url_for('ghp_table'))
    
    return render_template('index.html', bom=initial_data['bom'])

@app.route('/ghp_table')
def ghp_table():
    demand = initial_data['ghp_table']['rows']['Przewidywany popyt']
    production = initial_data['ghp_table']['rows']['Produkcja']
    stock = initial_data['ghp_table']['rows']['Aktualny stan']
    initial_stock = initial_data['initial_stock']['Łóżko']
    batch_size = initial_data['batch_sizes']['Łóżko']

    for i in range(8):
        if i == 0:
            stock[i] = initial_stock - demand[i]
        else:
            stock[i] = stock[i-1] - demand[i]
        
        if stock[i] < 0:
            required = -stock[i]
            production[i-1] = (required // batch_size) * batch_size
            if required % batch_size != 0:
                production[i-1] += batch_size
            stock[i] += production[i-1]
        else:
            production[i] = 0

    return render_template('ghp_table.html', ghp_table=initial_data['ghp_table'])

@app.route('/mrp_tables', methods=['GET', 'POST'])
def mrp_tables():
    if request.method == 'POST':
        if 'confirm' in request.form:
            for part in initial_data['mrp_tables']:
                update_planned_receipts(part)
                recalculate_stock(part)
                update_dependent_components(part)
            return redirect(url_for('mrp_tables'))
        else:
            part = request.form['part']
            week = int(request.form['week'])
            field = request.form['field']
            value = int(request.form['value'])
            
            if part not in initial_data['mrp_tables']:
                initial_data['mrp_tables'][part] = create_empty_mrp_table(part)
            
            initial_data['mrp_tables'][part][field][week] = value
            return jsonify({'status': 'success'})
    
    if not initial_data['mrp_tables']:
        for part in initial_data['bom']:
            if part != 'Łóżko':
                initial_data['mrp_tables'][part] = create_empty_mrp_table(part)
                calculate_initial_demand(part)
                recalculate_stock(part)
    
    return render_template(
        'mrp_tables.html',
        mrp_tables=initial_data['mrp_tables'],
        ghp_table=initial_data['ghp_table'],
        batch_sizes=initial_data['batch_sizes'],
        bom=initial_data['bom']
    )

def create_empty_mrp_table(part):
    return {
        'Całkowite zapotrzebowanie': [0] * 8,
        'Planowane przyjęcia': [0] * 8,
        'Przewidywane na stanie': [0] * 8,
        'Zapotrzebowanie netto': [0] * 8,
        'Planowane zamówienia': [0] * 8,
        'Planowane przyjęcie zamówień': [0] * 8,
        'Używane w': find_parents(part)
    }

def find_parents(part):
    parents = []
    for parent, data in initial_data['bom'].items():
        if 'components' in data and part in data['components']:
            parents.append(parent)
    return parents

def calculate_initial_demand(part):
    if part in ['Zagłówek', 'Stelaż', 'Rama łóżka']:
        bed_production = initial_data['ghp_table']['rows']['Produkcja']
        quantity_per_bed = initial_data['bom']['Łóżko']['components'][part]
        for week in range(8):
            initial_data['mrp_tables'][part]['Całkowite zapotrzebowanie'][week] = bed_production[week] * quantity_per_bed
    else:
        for parent in initial_data['mrp_tables'][part]['Używane w']:
            if parent in initial_data['mrp_tables']:
                parent_orders = initial_data['mrp_tables'][parent]['Planowane zamówienia']
                quantity_per_parent = initial_data['bom'][parent]['components'][part]
                for week in range(8):
                    initial_data['mrp_tables'][part]['Całkowite zapotrzebowanie'][week] += parent_orders[week] * quantity_per_parent

def update_planned_receipts(part):
    mrp = initial_data['mrp_tables'][part]
    lead_time = initial_data['bom'][part]['time']
    
    for week in range(8):
        if mrp['Planowane zamówienia'][week] > 0:
            receipt_week = min(week + lead_time, 7)
            mrp['Planowane przyjęcie zamówień'][receipt_week] = mrp['Planowane zamówienia'][week]

def recalculate_stock(part):
    mrp = initial_data['mrp_tables'][part]
    initial_stock = initial_data['initial_stock'].get(part, 0)
    stop_calculation = False
    
    for week in range(8):
        if stop_calculation:
            mrp['Przewidywane na stanie'][week] = 0
            mrp['Zapotrzebowanie netto'][week] = 0
            continue
            
        if week == 0:
            previous_stock = initial_stock
        else:
            previous_stock = mrp['Przewidywane na stanie'][week-1]
        
        mrp['Przewidywane na stanie'][week] = (
            previous_stock + 
            mrp['Planowane przyjęcia'][week] + 
            mrp['Planowane przyjęcie zamówień'][week] - 
            mrp['Całkowite zapotrzebowanie'][week]
        )
        
        mrp['Zapotrzebowanie netto'][week] = max(-mrp['Przewidywane na stanie'][week], 0)
        
        if mrp['Zapotrzebowanie netto'][week] > 0:
            stop_calculation = True

def update_dependent_components(part):
    for component, mrp in initial_data['mrp_tables'].items():
        if part in mrp['Używane w']:
            calculate_initial_demand(component)
            recalculate_stock(component)
            update_dependent_components(component)

if __name__ == '__main__':
    app.run(debug=True)