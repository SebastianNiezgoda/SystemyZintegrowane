from flask import Flask, render_template, request, jsonify
import math

app = Flask(__name__)

DEFAULT_PERIODS = [1, 2, 3, 4, 5, 6]
COMPONENTS = {
    'bed': {'name': 'Łóżko', 'bom_level': 0, 'initial_inventory': 5, 'lead_time': 1, 'lot_size': 10},
    'headboard': {'name': 'Zagłówek', 'bom_level': 1, 'initial_inventory': 10, 'lead_time': 1, 'lot_size': 50, 'multiplier': 1},
    'mattress_base': {'name': 'Stelaż pod materac', 'bom_level': 1, 'initial_inventory': 8, 'lead_time': 1, 'lot_size': 60, 'multiplier': 1},
    'center_beam': {'name': 'Środkowa belka wzmacniająca', 'bom_level': 2, 'initial_inventory': 15, 'lead_time': 1, 'lot_size': 60, 'multiplier': 1},
    'slats': {'name': 'Listwy sprężynujące', 'bom_level': 2, 'initial_inventory': 30, 'lead_time': 1, 'lot_size': 40, 'multiplier': 10},
    'bed_frame': {'name': 'Rama łóżka', 'bom_level': 1, 'initial_inventory': 12, 'lead_time': 1, 'lot_size': 40, 'multiplier': 1},
    'frame_beams': {'name': 'Belki ramy', 'bom_level': 2, 'initial_inventory': 20, 'lead_time': 1, 'lot_size': 50, 'multiplier': 4},
    'legs': {'name': 'Nogi', 'bom_level': 2, 'initial_inventory': 16, 'lead_time': 1, 'lot_size': 80, 'multiplier': 4}
}

@app.route('/')
def index():
    return render_template('index.html', 
                         periods=DEFAULT_PERIODS,
                         initial_inventory=COMPONENTS['bed']['initial_inventory'],
                         initial_lead_time=COMPONENTS['bed']['lead_time'])

@app.route('/calculate_ghp', methods=['POST'])
def calculate_ghp():
    try:
        data = request.json
        periods = data.get('periods', DEFAULT_PERIODS)
        demand = data['demand'][:len(periods)]
        inventory = data['inventory']
        lead_time = data['lead_time']
        
        available = []
        production = [0] * len(periods)
        current_inventory = inventory
        
        for i in range(len(periods)):
            current_inventory -= demand[i]
            if current_inventory < 0:
                order_period = i - lead_time
                if order_period >= 0:
                    production[order_period] = math.ceil(-current_inventory / 10) * 10
                    current_inventory += production[order_period]
            available.append(current_inventory)
        
        return jsonify({
            'available': available,
            'production': production,
            'components': {k: v for k, v in COMPONENTS.items() if k != 'bed'},
            'periods': periods
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/calculate_mrp', methods=['POST'])
def calculate_mrp():
    try:
        data = request.json
        periods = data.get('periods', DEFAULT_PERIODS)
        demand = data['demand'][:len(periods)]
        inventory = data['inventory']
        lead_time = data['lead_time']
        lot_size = max(1, data['lot_size'])
        manual_receipts = data.get('manual_receipts', [0]*len(periods))[:len(periods)]
        
        projected_on_hand = []
        net_requirements = [0] * len(periods)
        planned_orders = [0] * len(periods)
        planned_order_receipts = [0] * len(periods)
        current_inventory = inventory
        
        for i in range(len(periods)):
            current_inventory = current_inventory - demand[i] + manual_receipts[i]
            
            if current_inventory < 0:
                net_requirements[i] = -current_inventory
                order_qty = math.ceil(net_requirements[i] / lot_size) * lot_size
                order_period = i - lead_time
                
                if order_period >= 0:
                    planned_orders[order_period] = order_qty
                    planned_order_receipts[i] = order_qty
                    current_inventory += order_qty
            
            projected_on_hand.append(current_inventory)
        
        return jsonify({
            'projected_on_hand': projected_on_hand,
            'net_requirements': net_requirements,
            'planned_orders': planned_orders,
            'planned_order_receipts': planned_order_receipts,
            'manual_receipts': manual_receipts
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)