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
        'Stelaż': {'time': 1, 'batch_size': 100, 'components': {'Belka wzmacniająca': 1, 'Listwy sprężynujące': 1}},
        'Rama łóżka': {'time': 1, 'batch_size': 50, 'components': {'Belki ramy': 1, 'Nogi': 4}},
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
        mrp_tables[part] = calculate_mrp(part)
    return render_template('mrp_tables.html', mrp_tables=mrp_tables)

def calculate_mrp(part):
    mrp = {
        'Całkowite zapotrzebowanie': [0] ,
        'Planowane przyjęcia': [0] ,
        'Przewidywane na stanie': [0] ,
        'Zapotrzebowanie netto': [0] ,
        'Planowane zamówienia': [0] ,
        'Planowane przyjęcie zamówień': [0] ,
    }

    

    return mrp

if __name__ == '__main__':
    app.run(debug=True)