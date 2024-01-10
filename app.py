from flask import Flask, render_template, jsonify, request
import json
import threading
import os
from recovery import fast_scan, recover_file, read_temp_scan, recover_all, get_status, save_status
from flask_cors import CORS

app = Flask(__name__, static_url_path='/static')
CORS(app)

def get_max_address(status):
    max_address = 0

    for file_format, addresses in status.items():
        if not addresses:
            continue
        new_max = max(addresses)
        if new_max > max_address:
            max_address = new_max

    return max_address 


@app.route('/')
def index():
    status_json = read_temp_scan('C')

    max_address = get_max_address(status_json)
    dl = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    drives = [drive for drive in dl if os.path.exists(f'{drive}:')]

    return render_template('index.html', status=status_json, max_address=max_address, drives=drives)


@app.route('/drives')
def drives():
    dl = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    drives = [drive for drive in dl if os.path.exists(f'{drive}:')]
    return jsonify(drives=drives), 200


@app.route('/status')
def status():
    disk = request.args.get('disk').replace(':', '')
    status_json = read_temp_scan(disk)
    for format in status_json.keys():
        status_json[format] = len(status_json[format])
    state = get_status()

    return jsonify(data=status_json, state=state)


@app.route('/files')
def list_files():
    disk = request.args.get('disk').replace(':', '')
    file_format = request.args.get('format')
    
    status_json = read_temp_scan(disk)
    files = status_json.get(file_format)[:100]

    return jsonify(files=files), 200


@app.route('/start')
def start_scanner():
    disk = request.args.get('disk').replace(':', '')

    status_json = read_temp_scan(disk)

    save_status({'running': True})

    max_address = get_max_address(status_json)
    scanner_thread = threading.Thread(target=fast_scan, args=(disk, max_address,), daemon=True)
    scanner_thread.start()

    return jsonify(status='ok')


@app.route('/recover')
def recover():
    disk = request.args.get('disk').replace(':', '')

    file_format = request.args.get('format')
    address = int(request.args.get('address'))

    print(f'Recovering {disk}:\{address}{file_format}')

    recovery_thread = threading.Thread(target=recover_file, args=(file_format, address,), kwargs={'disk': disk} ,daemon=True)
    recovery_thread.start()
    
    # recover_file(file_format, address, disk=disk)
    return jsonify(status='ok')


@app.route('/recover_all')
def recover_all_endpoint():
    disk = request.args.get('disk').replace(':', '')
    file_format = request.args.get('format')

    found_files = read_temp_scan(disk)

    recovery_thread = threading.Thread(target=recover_all, args=(file_format, found_files[file_format],), kwargs={'disk': disk}, daemon=True)
    recovery_thread.start()

    return jsonify(status='ok')


@app.route('/stop')
def stop_scanner():
    print()
    save_status({'running': False, 'recovering': False})
    return jsonify(status='ok')


@app.route('/reset')
def reset_scanner():
    with open('temp_status.json', 'w+') as tmp_file:
        tmp_file.write(json.dumps({}))
    return jsonify(status='ok')


if __name__ == '__main__':
    app.run(debug=True)
