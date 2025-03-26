from flask import Flask, render_template, request, redirect, url_for
from collections import defaultdict

app = Flask(__name__)

# Inicjalizacja danych
initial_data = {
    'initial_stock': {},
    'ghp_table': {
        'weeks': [f'Week {i+1}' for i in range(8)],
        'rows': {
            'Przewidywany popyt': [0] * 8,  # Popyt na łóżko
            'Produkcja': [0] * 8,           # Produkcja łóżka (w partiach po 20 sztuk)
            'Aktualny stan': [0] * 8        # Aktualny stan łóżka
        }
    },
    'bom': {
        'Łóżko': {'time': 1, 'batch_size': 20, 'components': {'Zagłówek': 1, 'Stelaż': 1, 'Rama łóżka': 1}},
        'Stelaż': {'time': 1, 'batch_size': 100, 'components': {'Belka wzmacniająca': 1, 'Listwy sprężynujące': 8}},
        'Rama łóżka': {'time': 1, 'batch_size': 50, 'components': {'Belki ramy': 4, 'Nogi': 4}},
        'Zagłówek': {'time': 2, 'batch_size': 100},
        'Belka wzmacniająca': {'time': 1, 'batch_size': 50},
        'Listwy sprężynujące': {'time': 1, 'batch_size': 100},
        'Belki ramy': {'time': 1, 'batch_size': 100},
        'Nogi': {'time': 2, 'batch_size': 400}
    }
}

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Pobierz początkowy stan produktu i części
        initial_data['initial_stock']['Łóżko'] = int(request.form['initial_stock_product'])
        for part in initial_data['bom']:
            if part != 'Łóżko':  # Początkowy stan części
                initial_data['initial_stock'][part] = int(request.form[f'initial_stock_{part}'])
        # Pobierz przewidywany popyt na łóżko
        initial_data['ghp_table']['rows']['Przewidywany popyt'] = [int(request.form[f'demand_week_{i+1}']) for i in range(8)]
        return redirect(url_for('ghp_table'))
    return render_template('index.html', bom=initial_data['bom'])

@app.route('/ghp_table')
def ghp_table():
    # Oblicz produkcję i aktualny stan na podstawie popytu
    demand = initial_data['ghp_table']['rows']['Przewidywany popyt']
    production = initial_data['ghp_table']['rows']['Produkcja']
    stock = initial_data['ghp_table']['rows']['Aktualny stan']
    initial_stock = initial_data['initial_stock']['Łóżko']
    batch_size = initial_data['bom']['Łóżko']['batch_size']  # Wielkość partii (20 sztuk)

    for i in range(8):
        if i == 0:
            stock[i] = initial_stock - demand[i]
        else:
            stock[i] = stock[i-1] - demand[i]
        
        # Jeśli stan jest ujemny, zaplanuj produkcję w partiach
        if stock[i] < 0:
            required = -stock[i]  # Brakujący stan
            production[i-1] = (required // batch_size) * batch_size
            if required % batch_size != 0:
                production[i-1] += batch_size  # Dodaj kolejną partię, jeśli potrzeba
            stock[i] += production[i-1]
        else:
            production[i] = 0

    return render_template('ghp_table.html', ghp_table=initial_data['ghp_table'])

@app.route('/mrp_tables')
def mrp_tables():
    mrp_tables = {}
    for part in initial_data['bom']:
        if part != 'Łóżko':
            # Ustaw domyślny stan początkowy na 0 jeśli nie został podany
            if part not in initial_data['initial_stock']:
                initial_data['initial_stock'][part] = 0
                
            mrp = calculate_mrp(part)
            if mrp:
                mrp_tables[part] = mrp
    return render_template('mrp_tables.html', mrp_tables=mrp_tables)

def calculate_mrp(part):
    if part == 'Łóżko':
        return None
    
    mrp = {
        'Całkowite zapotrzebowanie': [0] * 8,
        'Planowane przyjęcia': [0] * 8,
        'Przewidywane na stanie': [0] * 8,
        'Zapotrzebowanie netto': [0] * 8,
        'Planowane zamówienia': [0] * 8,
        'Planowane przyjęcie zamówień': [0] * 8,
        'Używane w': []  # Nowe pole przechowujące informacje o rodzicach
    }
    
    # Znajdź wszystkie komponenty, które używają tej części
    for parent, data in initial_data['bom'].items():
        if 'components' in data and part in data['components']:
            mrp['Używane w'].append(parent)

    initial_stock = initial_data['initial_stock'].get(part, 0)
    batch_size = initial_data['bom'][part]['batch_size']
    lead_time = initial_data['bom'][part]['time']

    # Oblicz całkowite zapotrzebowanie 
    bed_production = initial_data['ghp_table']['rows']['Produkcja']
    if part in initial_data['bom']['Łóżko']['components']:
        quantity_per_bed = initial_data['bom']['Łóżko']['components'][part]
        for week in range(8):
            mrp['Całkowite zapotrzebowanie'][week] = bed_production[week] * quantity_per_bed
    else:
        for component, data in initial_data['bom'].items():
            if 'components' in data and part in data['components']:
                quantity_per_component = data['components'][part]
                if component in initial_data['bom']['Łóżko']['components']:
                    quantity_per_bed = initial_data['bom']['Łóżko']['components'][component]
                    for week in range(8):
                        mrp['Całkowite zapotrzebowanie'][week] = bed_production[week] * quantity_per_bed * quantity_per_component

    
        
        

    return mrp
if __name__ == '__main__':
    app.run(debug=True)

    