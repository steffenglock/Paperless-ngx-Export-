import json
import os
import requests
from flask import Flask, render_template_string, jsonify, request

app = Flask(__name__)
CONFIG_FILE = '/data/config.json'

# --- ROBUSTE KONFIGURATION 107---
def load_config():
    default = {"url": "", "token": ""}
    if not os.path.exists(CONFIG_FILE):
        return default
    try:
        with open(CONFIG_FILE, 'r') as f:
            content = f.read().strip()
            if not content:
                return default
            data = json.loads(content)
            return data if isinstance(data, dict) else default
    except Exception:
        return default

def save_config(url, token):
    url = url.rstrip('/')
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump({"url": url, "token": token}, f)

# Globaler Cache für Metadaten
meta = {
    'correspondents': {},
    'document_types': {},
    'storage_paths': {},
    'tags': {}
}

def get_headers():
    conf = load_config()
    return {"Authorization": f"Token {conf.get('token', '')}"}

def fetch_all_meta():
    conf = load_config()
    if not conf.get('url') or not conf.get('token'):
        return
    
    base = f"{conf['url']}/api"
    endpoints = {
        'correspondents': 'correspondents',
        'document_types': 'document_types',
        'storage_paths': 'storage_paths',
        'tags': 'tags'
    }
    for key, endpoint in endpoints.items():
        try:
            r = requests.get(f"{base}/{endpoint}/?page_size=1000", headers=get_headers(), timeout=5)
            if r.status_code == 200:
                meta[key] = {item['id']: item['name'] for item in r.json().get('results', [])}
        except Exception:
            meta[key] = {}

# --- HTML / UI ---
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Paperless Export</title>
    <style>
        :root { --primary: #1a73e8; --bg: #f8f9fa; --border: #dadce0; }
        body { font-family: 'Segoe UI', Tahoma, sans-serif; background: var(--bg); margin: 0; padding: 20px; color: #3c4043; }
        .container { max-width: 1400px; margin: auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.12); }
        
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 20px; margin-bottom: 20px; }
        .header h1 { margin: 0; color: var(--primary); font-size: 24px; }
        
        .filter-section { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .filter-card { display: flex; flex-direction: column; gap: 8px; }
        .filter-card label { font-weight: 600; font-size: 13px; color: #5f6368; }
        
        .date-container { grid-column: 1 / -1; display: flex; gap: 15px; align-items: center; background: #f1f3f4; padding: 15px; border-radius: 8px; flex-wrap: wrap; }
        
        input, select, button { padding: 10px; border: 1px solid var(--border); border-radius: 6px; font-size: 14px; outline: none; }
        input:focus, select:focus { border-color: var(--primary); }
        
        .btn-group { display: flex; gap: 10px; margin: 20px 0; }
        .btn { cursor: pointer; border: none; font-weight: bold; transition: opacity 0.2s; padding: 10px 20px;}
        .btn-primary { background: var(--primary); color: white; }
        .btn-success { background: #1e8e3e; color: white; }
        .btn:hover { opacity: 0.9; }

        .toggles { display: flex; flex-wrap: wrap; gap: 15px; font-size: 14px; padding: 15px; border: 1px solid #eee; border-radius: 8px; margin-bottom: 20px; background: #e8f0fe; }

        .table-wrapper { width: 100%; overflow-x: auto; margin-top: 10px; border: 1px solid var(--border); border-radius: 8px; }
        table { 
            width: 100%; 
            table-layout: auto; 
            border-collapse: collapse; 
            font-size: 14px; 
        }
        th, td { 
            padding: 12px; 
            border-bottom: 1px solid #f1f1f1; 
            text-align: left;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            vertical-align: top;
        }
        th { 
            background: #f8f9fa; 
            cursor: pointer; 
            color: #333; 
            position: relative;
            user-select: none;
            padding-right: 28px;
        }
        th:hover { background: #f1f3f4; }

        th.sorted-asc::after {
            content: "▲";
            position: absolute;
            right: 10px;
            color: var(--primary);
            font-size: 11px;
        }
        th.sorted-desc::after {
            content: "▼";
            position: absolute;
            right: 10px;
            color: var(--primary);
            font-size: 11px;
        }
        
        th.c0, td.c0 { width: 1%; max-width: 10ch; }
        th.c1, td.c1 { width: 1%; max-width: 10ch; }
        th.c2, td.c2 { max-width: 32ch; }
        th.c3, td.c3 { max-width: 24ch; }
        th.c4, td.c4 { max-width: 30ch; }
        th.c5, td.c5 { max-width: 22ch; }
        th.c6, td.c6 { max-width: 30ch; }
        th.c7, td.c7 { max-width: 16ch; }

        td.c2 a {
            color: var(--primary);
            text-decoration: none;
            display: inline-block;
            max-width: 100%;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            vertical-align: top;
        }
        td.c2 a:hover {
            text-decoration: underline;
        }

        .hidden { display: none !important; }
        
        #modal { display: none; position: fixed; top:0; left:0; width:100%; height:100%; background: rgba(0,0,0,0.5); z-index: 1000; justify-content: center; align-items: center; }
        .modal-content { background: white; padding: 30px; border-radius: 12px; width: 400px; box-shadow: 0 24px 38px rgba(0,0,0,0.14); }

        .cfg-field { margin-bottom: 16px; }
        .cfg-label {
            display: inline-block;
            margin-bottom: 6px;
            font-weight: 600;
            font-size: 14px;
            color: #3c4043;
            cursor: help;
        }
        .cfg-input {
            width: 100%;
            box-sizing: border-box;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Paperless-ngx Export v1.0.9</h1>
            <button class="btn" style="background:none; font-size:24px; padding:0;" onclick="document.getElementById('modal').style.display='flex'">⚙️</button>
        </div>

        <div class="filter-section">
            <div class="filter-card">
                <label>Volltextsuche</label>
                <input type="text" id="f_query" placeholder="Suchen...">
            </div>
            <div class="filter-card">
                <label>Korrespondent</label>
                <select id="f_corr"><option value="">Alle</option>{% for id, name in meta.correspondents.items() %}<option value="{{id}}">{{name}}</option>{% endfor %}</select>
            </div>
            <div class="filter-card">
                <label>Dokumententyp</label>
                <select id="f_type"><option value="">Alle</option>{% for id, name in meta.document_types.items() %}<option value="{{id}}">{{name}}</option>{% endfor %}</select>
            </div>
            <div class="filter-card">
                <label>Tags</label>
                <select id="f_tag"><option value="">Alle</option>{% for id, name in meta.tags.items() %}<option value="{{id}}">{{name}}</option>{% endfor %}</select>
            </div>
            <div class="filter-card">
                <label>Speicherpfad</label>
                <select id="f_path"><option value="">Alle</option>{% for id, name in meta.storage_paths.items() %}<option value="{{id}}">{{name}}</option>{% endfor %}</select>
            </div>
            
            <div class="date-container">
                <div class="filter-card">
                    <label>Filtertyp</label>
                    <select id="f_date_mode">
                        <option value="created">Datum: Ausgestellt</option>
                        <option value="added">Datum: Hinzugefügt</option>
                    </select>
                </div>
                <div class="filter-card">
                    <label>Von</label>
                    <input type="date" id="f_date_gte">
                </div>
                <div class="filter-card">
                    <label>Bis</label>
                    <input type="date" id="f_date_lte">
                </div>
            </div>
        </div>

        <div class="toggles">
            <strong>Sichtbare Spalten:</strong>
            <label><input type="checkbox" checked onchange="toggle(0)"> Ausgestellt</label>
            <label><input type="checkbox" onchange="toggle(1)"> Hinzugefügt</label>
            <label><input type="checkbox" checked onchange="toggle(2)"> Titel</label>
            <label><input type="checkbox" checked onchange="toggle(3)"> Korrespondent</label>
            <label><input type="checkbox" onchange="toggle(4)"> Tags</label>
            <label><input type="checkbox" onchange="toggle(5)"> Typ</label>
            <label><input type="checkbox" onchange="toggle(6)"> Pfad</label>
            <label><input type="checkbox" checked onchange="toggle(7)"> Wert</label>
        </div>

        <div class="btn-group">
            <button class="btn btn-primary" onclick="load()">🔍 Dokumente laden</button>
            <button class="btn btn-success" onclick="exportCSV()">📥 CSV Export</button>
        </div>

        <div id="status" style="margin-bottom:10px; font-weight:bold; color: var(--primary);"></div>

        <div class="table-wrapper">
            <table id="target">
                <thead>
                    <tr>
                        <th class="c0" onclick="sort(0)">Ausgestellt</th>
                        <th class="c1 hidden" onclick="sort(1)">Hinzugefügt</th>
                        <th class="c2" onclick="sort(2)">Titel</th>
                        <th class="c3" onclick="sort(3)">Korrespondent</th>
                        <th class="c4 hidden" onclick="sort(4)">Tags</th>
                        <th class="c5 hidden" onclick="sort(5)">Typ</th>
                        <th class="c6 hidden" onclick="sort(6)">Pfad</th>
                        <th class="c7" onclick="sort(7)">Wert</th>
                    </tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>
    </div>

    <div id="modal">
        <div class="modal-content">
            <h3>API Konfiguration</h3>

            <div class="cfg-field">
                <label class="cfg-label" for="cfg_url" title="Trage hier die vollständige Basis-URL deiner Paperless-ngx-Instanz ein. Du findest sie in der Adresszeile deines Browsers, wenn du Paperless öffnest. Beispiel: http://192.168.178.102:8010. Bitte ohne nachgestellten Slash eingeben.">
                    Paperless-ngx Basis-URL
                </label>
                <input type="text" id="cfg_url" class="cfg-input" placeholder="z. B. http://192.168.178.102:8010" value="{{conf.url}}">
            </div>

            <div class="cfg-field">
                <label class="cfg-label" for="cfg_token" title="Trage hier deinen API-Token aus Paperless-ngx ein. Du findest ihn in Paperless im Benutzerprofil bzw. in den Einstellungen zum API-Zugriff. Kopiere den kompletten Token unverändert. Ohne gültigen Token kann die Abfrage nicht funktionieren.">
                    Paperless-ngx API-Token
                </label>
                <input type="password" id="cfg_token" class="cfg-input" placeholder="API-Token einfügen" value="{{conf.token}}">
            </div>

            <button class="btn btn-primary" onclick="save()">Speichern & Neustart</button>
            <button class="btn" onclick="document.getElementById('modal').style.display='none'">Abbrechen</button>
        </div>
    </div>

    <script>
        let currentSort = { column: -1, direction: "asc" };

        function toggle(idx) {
            const th = document.querySelector(`th.c${idx}`);
            th.classList.toggle('hidden');
            
            document.querySelectorAll(`#target tbody tr`).forEach(row => {
                if (row.cells[idx]) {
                    row.cells[idx].classList.toggle('hidden');
                }
            });
        }

        async function save() {
            const url = document.getElementById('cfg_url').value;
            const token = document.getElementById('cfg_token').value;
            await fetch('/api/settings', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({url, token})
            });
            location.reload();
        }

        async function load() {
            const st = document.getElementById('status');
            st.innerText = "Lade Dokumente...";
            
            const params = new URLSearchParams();
            const mode = document.getElementById('f_date_mode').value;
            
            const map = {
                'f_query': 'query',
                'f_corr': 'correspondent__id',
                'f_type': 'document_type__id',
                'f_path': 'storage_path__id',
                'f_tag': 'tags__id__all'
            };
            
            for (let id in map) {
                const val = document.getElementById(id).value;
                if (val) params.append(map[id], val);
            }
            
            const gte = document.getElementById('f_date_gte').value;
            const lte = document.getElementById('f_date_lte').value;
            if (gte) params.append(`${mode}__date__gte`, gte);
            if (lte) params.append(`${mode}__date__lte`, lte);

            try {
                const r = await fetch(`/api/data?${params.toString()}`);
                const data = await r.json();
                const tbody = document.querySelector("#target tbody");
                tbody.innerHTML = "";
                
                data.forEach(d => {
                    const tr = document.createElement('tr');
                    const cols = [d.created, d.added, d.title, d.corr, d.tags, d.type, d.path, d.val];
                    
                    cols.forEach((val, i) => {
                        const td = document.createElement('td');
                        td.className = `c${i}`;
                        
                        if (i === 2) {
                            const a = document.createElement('a');
                            a.href = d.link || '#';
                            a.target = '_blank';
                            a.rel = 'noopener noreferrer';
                            a.innerText = val;
                            a.title = val || "";
                            td.appendChild(a);
                            td.title = val || "";
                        } else {
                            td.innerText = val;
                            td.title = val || "";
                        }

                        if (document.querySelector(`th.c${i}`).classList.contains('hidden')) {
                            td.classList.add('hidden');
                        }
                        tr.appendChild(td);
                    });
                    
                    tbody.appendChild(tr);
                });
                st.innerText = data.length + " Dokumente geladen.";
            } catch (e) {
                st.innerText = "Fehler beim Laden!";
            }
        }

        function sort(n) {
            const table = document.getElementById("target");
            const tbody = table.tBodies[0];
            const rows = Array.from(tbody.rows);
            const headers = table.querySelectorAll("thead th");

            let dir = "asc";
            if (currentSort.column === n && currentSort.direction === "asc") {
                dir = "desc";
            }

            rows.sort((rowA, rowB) => {
                const x = (rowA.cells[n]?.innerText || "").toLowerCase().trim();
                const y = (rowB.cells[n]?.innerText || "").toLowerCase().trim();

                if (x < y) return dir === "asc" ? -1 : 1;
                if (x > y) return dir === "asc" ? 1 : -1;
                return 0;
            });

            tbody.innerHTML = "";
            rows.forEach(row => tbody.appendChild(row));

            headers.forEach(th => {
                th.classList.remove("sorted-asc", "sorted-desc");
            });

            headers[n].classList.add(dir === "asc" ? "sorted-asc" : "sorted-desc");
            currentSort = { column: n, direction: dir };
        }

        function exportCSV() {
            let csv = "Ausgestellt;Hinzugefügt;Titel;Korrespondent;Tags;Typ;Pfad;Wert\\n";
            document.querySelectorAll("#target tbody tr").forEach(row => {
                const cols = Array.from(row.cells);
                csv += cols.map(c => `"${c.innerText.replace(/"/g, '""')}"`).join(";") + "\\n";
            });
            const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
            const link = document.createElement("a");
            link.href = URL.createObjectURL(blob);
            link.download = "paperless_export.csv";
            link.click();
        }

        window.addEventListener('DOMContentLoaded', () => {
            const hasUrl = {{ 'true' if conf.url else 'false' }};
            const hasToken = {{ 'true' if conf.token else 'false' }};
            if (!hasUrl || !hasToken) {
                document.getElementById('modal').style.display = 'flex';
            }
        });
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    conf = load_config()
    fetch_all_meta()
    return render_template_string(HTML_TEMPLATE, meta=meta, conf=conf)

@app.route('/api/settings', methods=['POST'])
def settings():
    data = request.json
    save_config(data['url'], data['token'])
    return jsonify({"status": "ok"})

@app.route('/api/data')
def get_data():
    conf = load_config()
    if not conf.get('url'):
        return jsonify([])
    
    params = {k: v for k, v in request.args.to_dict().items() if v}
    params['page_size'] = 1000
    
    try:
        r = requests.get(f"{conf['url']}/api/documents/", headers=get_headers(), params=params, timeout=15)
        results = r.json().get('results', [])
        
        output = []
        for d in results:
            val = ""
            if d.get('custom_fields'):
                for cf in d['custom_fields']:
                    v = cf.get('value')
                    if v is not None and str(v).strip() != "":
                        val = str(v)
                        break

            output.append({
                "id": d.get('id', ''),
                "created": d.get('created', '').split('T')[0] if d.get('created') else "",
                "added": d.get('added', '').split('T')[0] if d.get('added') else "",
                "title": d.get('title', ''),
                "corr": meta['correspondents'].get(d.get('correspondent'), ""),
                "tags": ", ".join([meta['tags'].get(t, "") for t in d.get('tags', [])]),
                "type": meta['document_types'].get(d.get('document_type'), ""),
                "path": meta['storage_paths'].get(d.get('storage_path'), ""),
                "val": val,
                "link": f"{conf['url']}/paperless/documents/{d.get('id', '')}" if d.get('id') else ""
            })
        return jsonify(output)
    except Exception as e:
        print(f"Fehler beim Laden der API-Daten: {e}")
        return jsonify([]), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
