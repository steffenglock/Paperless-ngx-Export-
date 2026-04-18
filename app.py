import json
import os
import time
import requests
from flask import Flask, render_template_string, jsonify, request, Response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per minute"],
    storage_uri="memory://"
)

CONFIG_FILE = '/data/config.json'

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
            if not isinstance(data, dict):
                return default
            for k, v in default.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception:
        return default

def save_config(url, token):
    url = url.rstrip('/')
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump({"url": url, "token": token}, f)

META_TTL = 300

meta_cache = {
    'data': {
        'correspondents': {},
        'document_types': {},
        'storage_paths': {},
        'tags': {}
    },
    'last_fetch': 0
}

def get_headers():
    conf = load_config()
    return {"Authorization": "Token " + conf.get('token', '')}

def fetch_all_meta(force=False):
    now = time.time()
    if not force and (now - meta_cache['last_fetch']) < META_TTL:
        return
    conf = load_config()
    if not conf.get('url') or not conf.get('token'):
        return
    base = conf['url'] + "/api"
    endpoints = {
        'correspondents': 'correspondents',
        'document_types': 'document_types',
        'storage_paths': 'storage_paths',
        'tags': 'tags'
    }
    for key, endpoint in endpoints.items():
        try:
            r = requests.get(
                base + "/" + endpoint + "/?page_size=1000",
                headers=get_headers(),
                timeout=10
            )
            if r.status_code == 200:
                meta_cache['data'][key] = {
                    item['id']: item['name']
                    for item in r.json().get('results', [])
                }
        except Exception as e:
            print("Meta-Fetch Fehler (" + key + "): " + str(e))
            meta_cache['data'][key] = {}
    meta_cache['last_fetch'] = time.time()


HTML_TEMPLATE = (
    "<!DOCTYPE html>\n"
    "<html lang=\"de\">\n"
    "<head>\n"
    "<meta charset=\"UTF-8\">\n"
    "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
    "<title>Paperless Export</title>\n"
    "<style>\n"
    ":root{--primary:#1a73e8;--bg:#f8f9fa;--border:#dadce0;}\n"
    "body{font-family:'Segoe UI',Tahoma,sans-serif;background:var(--bg);margin:0;padding:20px;color:#3c4043;}\n"
    ".container{max-width:1400px;margin:auto;background:white;padding:30px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.12);}\n"
    ".header{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--border);padding-bottom:20px;margin-bottom:20px;}\n"
    ".header h1{margin:0;color:var(--primary);font-size:24px;}\n"
    ".header-right{display:flex;align-items:center;gap:16px;}\n"
    ".lang-switcher{display:flex;gap:6px;align-items:center;}\n"
    ".lang-btn{background:none;border:2px solid transparent;border-radius:4px;cursor:pointer;font-size:22px;padding:2px 4px;line-height:1;transition:border-color 0.2s,transform 0.1s;}\n"
    ".lang-btn:hover{transform:scale(1.15);}\n"
    ".lang-btn.active{border-color:var(--primary);}\n"
    ".filter-section{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:20px;margin-bottom:20px;}\n"
    ".filter-card{display:flex;flex-direction:column;gap:8px;}\n"
    ".filter-card label{font-weight:600;font-size:13px;color:#5f6368;}\n"
    ".date-container{grid-column:1/-1;display:flex;gap:15px;align-items:center;background:#f1f3f4;padding:15px;border-radius:8px;flex-wrap:wrap;}\n"
    "input,select,button{padding:10px;border:1px solid var(--border);border-radius:6px;font-size:14px;outline:none;}\n"
    "input:focus,select:focus{border-color:var(--primary);}\n"
    ".btn-group{display:flex;gap:10px;margin:20px 0;flex-wrap:wrap;}\n"
    ".btn{cursor:pointer;border:none;font-weight:bold;transition:opacity 0.2s;padding:10px 20px;border-radius:6px;font-size:14px;}\n"
    ".btn-primary{background:var(--primary);color:white;}\n"
    ".btn-success{background:#1e8e3e;color:white;}\n"
    ".btn:hover{opacity:0.9;}\n"
    ".toggles{display:flex;flex-wrap:wrap;gap:15px;font-size:14px;padding:15px;border:1px solid #eee;border-radius:8px;margin-bottom:20px;background:#e8f0fe;}\n"
    ".table-wrapper{width:100%;overflow-x:auto;margin-top:10px;border:1px solid var(--border);border-radius:8px;}\n"
    "table{width:100%;table-layout:auto;border-collapse:collapse;font-size:14px;}\n"
    "th,td{padding:12px;border-bottom:1px solid #f1f1f1;text-align:left;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;vertical-align:top;}\n"
    "th{background:#f8f9fa;cursor:pointer;color:#333;position:relative;user-select:none;padding-right:28px;}\n"
    "th:hover{background:#f1f3f4;}\n"
    "th.sorted-asc::after{content:'\\25B2';position:absolute;right:10px;color:var(--primary);font-size:11px;}\n"
    "th.sorted-desc::after{content:'\\25BC';position:absolute;right:10px;color:var(--primary);font-size:11px;}\n"
    "th.c0,td.c0{width:1%;max-width:10ch;}\n"
    "th.c1,td.c1{width:1%;max-width:10ch;}\n"
    "th.c2,td.c2{max-width:32ch;}\n"
    "th.c3,td.c3{max-width:24ch;}\n"
    "th.c4,td.c4{max-width:30ch;}\n"
    "th.c5,td.c5{max-width:22ch;}\n"
    "th.c6,td.c6{max-width:30ch;}\n"
    "th.c7,td.c7{max-width:16ch;}\n"
    "td.c2 a{color:var(--primary);text-decoration:none;display:inline-block;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;vertical-align:top;}\n"
    "td.c2 a:hover{text-decoration:underline;}\n"
    "tr:hover td{background:#f8f9ff;}\n"
    ".hidden{display:none !important;}\n"
    "#status{margin-bottom:10px;font-weight:bold;color:var(--primary);min-height:22px;}\n"
    ".status-error{color:#d93025 !important;}\n"
    "#modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);z-index:1000;justify-content:center;align-items:center;}\n"
    ".modal-content{background:white;padding:30px;border-radius:12px;width:440px;box-shadow:0 24px 38px rgba(0,0,0,0.14);}\n"
    ".modal-content h3{margin-top:0;color:var(--primary);}\n"
    ".cfg-field{margin-bottom:16px;}\n"
    ".cfg-label{display:inline-block;margin-bottom:6px;font-weight:600;font-size:14px;color:#3c4043;cursor:help;border-bottom:1px dotted #aaa;}\n"
    ".cfg-input{width:100%;box-sizing:border-box;}\n"
    ".token-wrapper{position:relative;display:flex;align-items:center;}\n"
    ".token-wrapper input{flex:1;padding-right:60px;}\n"
    ".token-toggle{position:absolute;right:4px;background:#f1f3f4;border:1px solid var(--border);cursor:pointer;font-size:12px;padding:4px 8px;color:#3c4043;border-radius:4px;white-space:nowrap;}\n"
    ".token-toggle:hover{background:var(--primary);color:white;border-color:var(--primary);}\n"
    ".cfg-hint{font-size:12px;color:#888;margin-top:4px;}\n"
    ".modal-btn-row{display:flex;gap:10px;margin-top:8px;flex-wrap:wrap;}\n"
    "#progress-bar-wrap{display:none;width:100%;background:#e8f0fe;border-radius:6px;margin-bottom:10px;overflow:hidden;height:8px;}\n"
    "#progress-bar{height:8px;background:var(--primary);width:0%;transition:width 0.3s;}\n"
    "</style>\n"
    "</head>\n"
    "<body>\n"
    "<div class=\"container\">\n"
    "  <div class=\"header\">\n"
    "    <div class=\"lang-switcher\">\n"
    "      <button class=\"lang-btn\" id=\"lang-de\" onclick=\"window.setLang('de')\" title=\"Deutsch\">&#127465;&#127466;</button>\n"
    "      <button class=\"lang-btn\" id=\"lang-fr\" onclick=\"window.setLang('fr')\" title=\"Francais\">&#127467;&#127479;</button>\n"
    "      <button class=\"lang-btn\" id=\"lang-en\" onclick=\"window.setLang('en')\" title=\"English\">&#127468;&#127463;</button>\n"
    "    </div>\n"
    "    <h1 id=\"main-title\">Paperless-ngx Export</h1>\n"
    "    <div class=\"header-right\">\n"
    "      <span id=\"status\"></span>\n"
    "      <button class=\"btn\" id=\"btn-settings\" style=\"background:none;font-size:22px;padding:4px;border:1px solid var(--border);border-radius:6px;\" title=\"Einstellungen\">&#9881;</button>\n"
    "    </div>\n"
    "  </div>\n"
    "\n"
    "  <div id=\"progress-bar-wrap\"><div id=\"progress-bar\"></div></div>\n"
    "\n"
    "  <div class=\"filter-section\">\n"
    "    <div class=\"filter-card\">\n"
    "      <label id=\"lbl-fulltext\">Volltextsuche</label>\n"
    "      <input type=\"text\" id=\"f_query\" placeholder=\"Suchen...\">\n"
    "    </div>\n"
    "    <div class=\"filter-card\">\n"
    "      <label id=\"lbl-correspondent\">Korrespondent</label>\n"
    "      <select id=\"f_corr\">\n"
    "        <option value=\"\" id=\"opt-all-corr\">Alle</option>\n"
    "        {% for cid, name in meta.correspondents.items() %}\n"
    "        <option value=\"{{ cid }}\">{{ name }}</option>\n"
    "        {% endfor %}\n"
    "      </select>\n"
    "    </div>\n"
    "    <div class=\"filter-card\">\n"
    "      <label id=\"lbl-doctype\">Dokumententyp</label>\n"
    "      <select id=\"f_type\">\n"
    "        <option value=\"\" id=\"opt-all-type\">Alle</option>\n"
    "        {% for did, name in meta.document_types.items() %}\n"
    "        <option value=\"{{ did }}\">{{ name }}</option>\n"
    "        {% endfor %}\n"
    "      </select>\n"
    "    </div>\n"
    "    <div class=\"filter-card\">\n"
    "      <label id=\"lbl-tags\">Tags</label>\n"
    "      <select id=\"f_tag\">\n"
    "        <option value=\"\" id=\"opt-all-tag\">Alle</option>\n"
    "        {% for tid, name in meta.tags.items() %}\n"
    "        <option value=\"{{ tid }}\">{{ name }}</option>\n"
    "        {% endfor %}\n"
    "      </select>\n"
    "    </div>\n"
    "    <div class=\"filter-card\">\n"
    "      <label id=\"lbl-storagepath\">Speicherpfad</label>\n"
    "      <select id=\"f_path\">\n"
    "        <option value=\"\" id=\"opt-all-path\">Alle</option>\n"
    "        {% for pid, name in meta.storage_paths.items() %}\n"
    "        <option value=\"{{ pid }}\">{{ name }}</option>\n"
    "        {% endfor %}\n"
    "      </select>\n"
    "    </div>\n"
    "    <div class=\"date-container\">\n"
    "      <div class=\"filter-card\">\n"
    "        <label id=\"lbl-datetype\">Filtertyp</label>\n"
    "        <select id=\"f_date_mode\">\n"
    "          <option value=\"created\" id=\"opt-date-created\">Datum: Ausgestellt</option>\n"
    "          <option value=\"added\" id=\"opt-date-added\">Datum: Hinzugefuegt</option>\n"
    "        </select>\n"
    "      </div>\n"
    "      <div class=\"filter-card\">\n"
    "        <label id=\"lbl-date-from\">Von</label>\n"
    "        <input type=\"date\" id=\"f_date_gte\">\n"
    "      </div>\n"
    "      <div class=\"filter-card\">\n"
    "        <label id=\"lbl-date-to\">Bis</label>\n"
    "        <input type=\"date\" id=\"f_date_lte\">\n"
    "      </div>\n"
    "    </div>\n"
    "  </div>\n"
    "\n"
    "  <div class=\"toggles\">\n"
    "    <strong id=\"lbl-visible-cols\">Sichtbare Spalten:</strong>\n"
    "    <label><input type=\"checkbox\" checked onchange=\"toggleCol(0)\"> <span id=\"tog0\">Ausgestellt</span></label>\n"
    "    <label><input type=\"checkbox\" onchange=\"toggleCol(1)\"> <span id=\"tog1\">Hinzugefuegt</span></label>\n"
    "    <label><input type=\"checkbox\" checked onchange=\"toggleCol(2)\"> <span id=\"tog2\">Titel</span></label>\n"
    "    <label><input type=\"checkbox\" checked onchange=\"toggleCol(3)\"> <span id=\"tog3\">Korrespondent</span></label>\n"
    "    <label><input type=\"checkbox\" onchange=\"toggleCol(4)\"> <span id=\"tog4\">Tags</span></label>\n"
    "    <label><input type=\"checkbox\" onchange=\"toggleCol(5)\"> <span id=\"tog5\">Typ</span></label>\n"
    "    <label><input type=\"checkbox\" onchange=\"toggleCol(6)\"> <span id=\"tog6\">Pfad</span></label>\n"
    "    <label><input type=\"checkbox\" checked onchange=\"toggleCol(7)\"> <span id=\"tog7\">Wert</span></label>\n"
    "  </div>\n"
    "\n"
    "  <div class=\"btn-group\">\n"
    "    <button class=\"btn btn-primary\" id=\"btn-load\" onclick=\"loadDocs()\">Dokumente laden</button>\n"
    "    <button class=\"btn btn-success\" id=\"btn-csv\" onclick=\"exportCSV()\">CSV Export</button>\n"
    "  </div>\n"
    "\n"
    "  <div class=\"table-wrapper\">\n"
    "    <table id=\"target\">\n"
    "      <thead><tr>\n"
    "        <th class=\"c0\" onclick=\"sortTable(0)\"><span id=\"th0\">Ausgestellt</span></th>\n"
    "        <th class=\"c1 hidden\" onclick=\"sortTable(1)\"><span id=\"th1\">Hinzugefuegt</span></th>\n"
    "        <th class=\"c2\" onclick=\"sortTable(2)\"><span id=\"th2\">Titel</span></th>\n"
    "        <th class=\"c3\" onclick=\"sortTable(3)\"><span id=\"th3\">Korrespondent</span></th>\n"
    "        <th class=\"c4 hidden\" onclick=\"sortTable(4)\"><span id=\"th4\">Tags</span></th>\n"
    "        <th class=\"c5 hidden\" onclick=\"sortTable(5)\"><span id=\"th5\">Typ</span></th>\n"
    "        <th class=\"c6 hidden\" onclick=\"sortTable(6)\"><span id=\"th6\">Pfad</span></th>\n"
    "        <th class=\"c7\" onclick=\"sortTable(7)\"><span id=\"th7\">Wert</span></th>\n"
    "      </tr></thead>\n"
    "      <tbody></tbody>\n"
    "    </table>\n"
    "  </div>\n"
    "</div>\n"
    "\n"
    "<div id=\"modal\">\n"
    "  <div class=\"modal-content\">\n"
    "    <h3 id=\"modal-title\">API Konfiguration</h3>\n"
    "    <div class=\"cfg-field\">\n"
    "      <label class=\"cfg-label\" id=\"lbl-url\" for=\"cfg_url\">Paperless-ngx Basis-URL</label>\n"
    "      <input type=\"text\" id=\"cfg_url\" class=\"cfg-input\"\n"
    "        placeholder=\"http://192.168.178.102:8010\"\n"
    "        value=\"{{ conf.url }}\">\n"
    "      <div class=\"cfg-hint\" id=\"hint-url\">Ohne nachgestellten Slash.</div>\n"
    "    </div>\n"
    "    <div class=\"cfg-field\">\n"
    "      <label class=\"cfg-label\" id=\"lbl-token\" for=\"cfg_token\">API-Token</label>\n"
    "      <div class=\"token-wrapper\">\n"
    "        <input type=\"password\" id=\"cfg_token\" class=\"cfg-input\"\n"
    "          placeholder=\"API-Token einfuegen\"\n"
    "          value=\"{{ conf.token }}\">\n"
    "        <button class=\"token-toggle\" id=\"token_eye\" type=\"button\">Anzeigen</button>\n"
    "      </div>\n"
    "      <div class=\"cfg-hint\" id=\"hint-token\">Profil &rarr; API-Token</div>\n"
    "    </div>\n"
    "    <div class=\"modal-btn-row\">\n"
    "      <button class=\"btn btn-primary\" id=\"btn-save\" type=\"button\">Speichern</button>\n"
    "      <button class=\"btn\" style=\"background:#f1f3f4;\" id=\"btn-cancel\" type=\"button\">Abbrechen</button>\n"
    "    </div>\n"
    "  </div>\n"
    "</div>\n"
    "\n"
    "<script>\n"
    "(function(){\n"
    "\n"
    "var HAS_URL   = {% if conf.url %}true{% else %}false{% endif %};\n"
    "var HAS_TOKEN = {% if conf.token %}true{% else %}false{% endif %};\n"
    "\n"
    "var T = {\n"
    "  de:{\n"
    "    title:'Paperless-ngx Export',\n"
    "    fulltext:'Volltextsuche (Titel + Inhalt)',\n"
    "    search_ph:'Suchbegriff...',\n"
    "    correspondent:'Korrespondent',\n"
    "    doctype:'Dokumententyp',\n"
    "    tags:'Tags',\n"
    "    storagepath:'Speicherpfad',\n"
    "    datetype:'Filtertyp',\n"
    "    date_created:'Datum: Ausgestellt',\n"
    "    date_added:'Datum: Hinzugefuegt',\n"
    "    date_from:'Von',\n"
    "    date_to:'Bis',\n"
    "    all:'Alle',\n"
    "    visible_cols:'Sichtbare Spalten:',\n"
    "    col:['Ausgestellt','Hinzugefuegt','Titel','Korrespondent','Tags','Typ','Pfad','Wert'],\n"
    "    btn_load:'Dokumente laden',\n"
    "    btn_csv:'CSV Export',\n"
    "    btn_save:'Speichern',\n"
    "    btn_cancel:'Abbrechen',\n"
    "    modal_title:'API Konfiguration',\n"
    "    lbl_url:'Paperless-ngx Basis-URL',\n"
    "    lbl_token:'Paperless-ngx API-Token',\n"
    "    hint_url:'Ohne nachgestellten Slash. Beispiel: http://192.168.1.10:8010',\n"
    "    hint_url_tt:'Vollstaendige Basis-URL der Paperless-ngx-Instanz, z.B. http://192.168.178.102:8010 - ohne abschliessenden Slash.',\n"
    "    hint_token:'Zu finden in Paperless unter Profil -> API-Token',\n"
    "    hint_token_tt:'Den API-Token findest du in Paperless-ngx unter: Benutzername oben rechts -> Profil -> Abschnitt API-Token. Token vollstaendig kopieren.',\n"
    "    token_ph:'API-Token einfuegen',\n"
    "    token_show:'Anzeigen',\n"
    "    token_hide:'Verbergen',\n"
    "    st_loading:'Lade Dokumente...',\n"
    "    st_page:'Lade Seite',\n"
    "    st_of:'von',\n"
    "    st_done:'Dokumente geladen.',\n"
    "    st_error:'Fehler beim Laden!',\n"
    "    csv_file:'paperless_export.csv'\n"
    "  },\n"
    "  fr:{\n"
    "    title:'Paperless-ngx Export',\n"
    "    fulltext:'Recherche plein texte (titre + contenu)',\n"
    "    search_ph:'Terme de recherche...',\n"
    "    correspondent:'Correspondant',\n"
    "    doctype:'Type de document',\n"
    "    tags:'Etiquettes',\n"
    "    storagepath:'Chemin de stockage',\n"
    "    datetype:'Type de filtre',\n"
    "    date_created:'Date: Emis',\n"
    "    date_added:'Date: Ajoute',\n"
    "    date_from:'Du',\n"
    "    date_to:'Au',\n"
    "    all:'Tous',\n"
    "    visible_cols:'Colonnes visibles:',\n"
    "    col:['Emis le','Ajoute le','Titre','Correspondant','Etiquettes','Type','Chemin','Valeur'],\n"
    "    btn_load:'Charger les documents',\n"
    "    btn_csv:'Export CSV',\n"
    "    btn_save:'Enregistrer',\n"
    "    btn_cancel:'Annuler',\n"
    "    modal_title:'Configuration API',\n"
    "    lbl_url:'URL de base Paperless-ngx',\n"
    "    lbl_token:'Token API Paperless-ngx',\n"
    "    hint_url:'Sans barre oblique finale. Exemple: http://192.168.1.10:8010',\n"
    "    hint_url_tt:'URL complete de Paperless-ngx, ex: http://192.168.178.102:8010 - sans barre oblique finale.',\n"
    "    hint_token:'Disponible dans Paperless sous Profil -> Token API',\n"
    "    hint_token_tt:'Le token API se trouve dans Paperless-ngx: cliquez sur votre nom en haut a droite -> Profil -> section Token API.',\n"
    "    token_ph:'Coller le token API',\n"
    "    token_show:'Afficher',\n"
    "    token_hide:'Masquer',\n"
    "    st_loading:'Chargement...',\n"
    "    st_page:'Page',\n"
    "    st_of:'sur',\n"
    "    st_done:'documents charges.',\n"
    "    st_error:'Erreur de chargement!',\n"
    "    csv_file:'paperless_export.csv'\n"
    "  },\n"
    "  en:{\n"
    "    title:'Paperless-ngx Export',\n"
    "    fulltext:'Full-text search (title + content)',\n"
    "    search_ph:'Search term...',\n"
    "    correspondent:'Correspondent',\n"
    "    doctype:'Document type',\n"
    "    tags:'Tags',\n"
    "    storagepath:'Storage path',\n"
    "    datetype:'Filter type',\n"
    "    date_created:'Date: Issued',\n"
    "    date_added:'Date: Added',\n"
    "    date_from:'From',\n"
    "    date_to:'To',\n"
    "    all:'All',\n"
    "    visible_cols:'Visible columns:',\n"
    "    col:['Issued','Added','Title','Correspondent','Tags','Type','Path','Value'],\n"
    "    btn_load:'Load documents',\n"
    "    btn_csv:'CSV Export',\n"
    "    btn_save:'Save',\n"
    "    btn_cancel:'Cancel',\n"
    "    modal_title:'API Configuration',\n"
    "    lbl_url:'Paperless-ngx Base URL',\n"
    "    lbl_token:'Paperless-ngx API Token',\n"
    "    hint_url:'No trailing slash. Example: http://192.168.1.10:8010',\n"
    "    hint_url_tt:'Full base URL of your Paperless-ngx instance, e.g. http://192.168.178.102:8010 - no trailing slash.',\n"
    "    hint_token:'Found in Paperless under Profile -> API Token',\n"
    "    hint_token_tt:'The API token is in Paperless-ngx: click your username top right -> Profile -> API Token section. Copy the full token.',\n"
    "    token_ph:'Paste API token',\n"
    "    token_show:'Show',\n"
    "    token_hide:'Hide',\n"
    "    st_loading:'Loading documents...',\n"
    "    st_page:'Loading page',\n"
    "    st_of:'of',\n"
    "    st_done:'documents loaded.',\n"
    "    st_error:'Error loading data!',\n"
    "    csv_file:'paperless_export.csv'\n"
    "  }\n"
    "};\n"
    "\n"
    "var lang = 'de';\n"
    "\n"
    "function detectLang(){\n"
    "  var saved = localStorage.getItem('paperless_lang');\n"
    "  if(saved && T[saved]) return saved;\n"
    "  var nav = (navigator.language||'de').toLowerCase();\n"
    "  if(nav.indexOf('fr')===0) return 'fr';\n"
    "  if(nav.indexOf('en')===0) return 'en';\n"
    "  return 'de';\n"
    "}\n"
    "\n"
    "function setLang(l){\n"
    "  if(!T[l]) return;\n"
    "  lang = l;\n"
    "  localStorage.setItem('paperless_lang', l);\n"
    "  var tr = T[l];\n"
    "  function txt(id,v){ var e=document.getElementById(id); if(e) e.textContent=v; }\n"
    "  function ph(id,v){ var e=document.getElementById(id); if(e) e.placeholder=v; }\n"
    "  function ti(id,v){ var e=document.getElementById(id); if(e) e.title=v; }\n"
    "  document.title = tr.title;\n"
    "  txt('main-title',      tr.title);\n"
    "  txt('lbl-fulltext',    tr.fulltext);\n"
    "  ph('f_query',          tr.search_ph);\n"
    "  txt('lbl-correspondent', tr.correspondent);\n"
    "  txt('lbl-doctype',     tr.doctype);\n"
    "  txt('lbl-tags',        tr.tags);\n"
    "  txt('lbl-storagepath', tr.storagepath);\n"
    "  txt('lbl-datetype',    tr.datetype);\n"
    "  txt('opt-date-created', tr.date_created);\n"
    "  txt('opt-date-added',  tr.date_added);\n"
    "  txt('lbl-date-from',   tr.date_from);\n"
    "  txt('lbl-date-to',     tr.date_to);\n"
    "  txt('opt-all-corr',    tr.all);\n"
    "  txt('opt-all-type',    tr.all);\n"
    "  txt('opt-all-tag',     tr.all);\n"
    "  txt('opt-all-path',    tr.all);\n"
    "  txt('lbl-visible-cols', tr.visible_cols);\n"
    "  for(var i=0;i<8;i++){\n"
    "    txt('tog'+i, tr.col[i]);\n"
    "    txt('th'+i,  tr.col[i]);\n"
    "  }\n"
    "  txt('btn-load',        tr.btn_load);\n"
    "  txt('btn-csv',         tr.btn_csv);\n"
    "  txt('btn-save',        tr.btn_save);\n"
    "  txt('btn-cancel',      tr.btn_cancel);\n"
    "  txt('modal-title',     tr.modal_title);\n"
    "  txt('lbl-url',         tr.lbl_url);\n"
    "  ti('lbl-url',          tr.hint_url_tt);\n"
    "  txt('lbl-token',       tr.lbl_token);\n"
    "  ti('lbl-token',        tr.hint_token_tt);\n"
    "  txt('hint-url',        tr.hint_url);\n"
    "  txt('hint-token',      tr.hint_token);\n"
    "  ph('cfg_token',        tr.token_ph);\n"
    "  var eye = document.getElementById('token_eye');\n"
    "  var inp = document.getElementById('cfg_token');\n"
    "  if(eye && inp){\n"
    "    eye.textContent = (inp.type==='text') ? tr.token_hide : tr.token_show;\n"
    "  }\n"
    "  ['de','fr','en'].forEach(function(x){\n"
    "    var b = document.getElementById('lang-'+x);\n"
    "    if(b) b.classList.toggle('active', x===l);\n"
    "  });\n"
    "}\n"
    "\n"
    "/* setLang global verfuegbar machen fuer onclick-Handler */\n"
    "window.setLang = setLang;\n"
    "\n"
    "/* Token anzeigen/verbergen */\n"
    "document.getElementById('token_eye').addEventListener('click', function(){\n"
    "  var inp = document.getElementById('cfg_token');\n"
    "  var tr  = T[lang];\n"
    "  if(inp.type==='password'){\n"
    "    inp.type='text';\n"
    "    this.textContent=tr.token_hide;\n"
    "  } else {\n"
    "    inp.type='password';\n"
    "    this.textContent=tr.token_show;\n"
    "  }\n"
    "});\n"
    "\n"
    "/* Einstellungen oeffnen */\n"
    "document.getElementById('btn-settings').addEventListener('click', function(){\n"
    "  document.getElementById('modal').style.display='flex';\n"
    "});\n"
    "\n"
    "/* Abbrechen */\n"
    "document.getElementById('btn-cancel').addEventListener('click', function(){\n"
    "  document.getElementById('modal').style.display='none';\n"
    "});\n"
    "\n"
    "/* Speichern */\n"
    "document.getElementById('btn-save').addEventListener('click', function(){\n"
    "  var url   = document.getElementById('cfg_url').value.trim();\n"
    "  var token = document.getElementById('cfg_token').value.trim();\n"
    "  if(!url || !token){ alert('Bitte URL und Token eingeben.'); return; }\n"
    "  fetch('/api/settings',{\n"
    "    method:'POST',\n"
    "    headers:{'Content-Type':'application/json'},\n"
    "    body:JSON.stringify({url:url, token:token})\n"
    "  })\n"
    "  .then(function(r){ return r.json(); })\n"
    "  .then(function(d){\n"
    "    if(d.status==='ok'){ location.reload(); }\n"
    "    else { alert('Fehler: '+(d.msg||'Unbekannt')); }\n"
    "  })\n"
    "  .catch(function(e){ alert('Verbindungsfehler: '+e); });\n"
    "});\n"
    "\n"
    "/* Spalten ein-/ausblenden */\n"
    "function toggleCol(idx){\n"
    "  var th=document.querySelector('.c'+idx);\n"
    "  if(!th) return;\n"
    "  th.classList.toggle('hidden');\n"
    "  document.querySelectorAll('#target tbody tr').forEach(function(row){\n"
    "    if(row.cells[idx]) row.cells[idx].classList.toggle('hidden');\n"
    "  });\n"
    "}\n"
    "window.toggleCol = toggleCol;\n"
    "\n"
    "/* Sortierung */\n"
    "var currentSort={column:-1,direction:'asc'};\n"
    "function sortTable(n){\n"
    "  var table=document.getElementById('target');\n"
    "  var tbody=table.tBodies[0];\n"
    "  var rows=Array.from(tbody.rows);\n"
    "  var headers=table.querySelectorAll('thead th');\n"
    "  var dir=(currentSort.column===n&&currentSort.direction==='asc')?'desc':'asc';\n"
    "  rows.sort(function(a,b){\n"
    "    var x=(a.cells[n]?a.cells[n].innerText:'').toLowerCase().trim();\n"
    "    var y=(b.cells[n]?b.cells[n].innerText:'').toLowerCase().trim();\n"
    "    var dx=Date.parse(x),dy=Date.parse(y);\n"
    "    if(!isNaN(dx)&&!isNaN(dy)) return dir==='asc'?dx-dy:dy-dx;\n"
    "    if(x<y) return dir==='asc'?-1:1;\n"
    "    if(x>y) return dir==='asc'?1:-1;\n"
    "    return 0;\n"
    "  });\n"
    "  tbody.innerHTML='';\n"
    "  rows.forEach(function(row){tbody.appendChild(row);});\n"
    "  headers.forEach(function(th){th.classList.remove('sorted-asc','sorted-desc');});\n"
    "  headers[n].classList.add(dir==='asc'?'sorted-asc':'sorted-desc');\n"
    "  currentSort={column:n,direction:dir};\n"
    "}\n"
    "window.sortTable = sortTable;\n"
    "\n"
    "/* Dokumente laden mit Paginierung */\n"
    "async function loadDocs(){\n"
    "  var st=document.getElementById('status');\n"
    "  var wrap=document.getElementById('progress-bar-wrap');\n"
    "  var bar=document.getElementById('progress-bar');\n"
    "  var tr=T[lang];\n"
    "  st.className='';\n"
    "  st.textContent=tr.st_loading;\n"
    "  wrap.style.display='block';\n"
    "  bar.style.width='0%';\n"
    "  var mode=document.getElementById('f_date_mode').value;\n"
    "  var query=document.getElementById('f_query').value.trim();\n"
    "  var params=new URLSearchParams();\n"
    "  if(query) params.append('query', query);\n"
    "  var map={\n"
    "    'f_corr':'correspondent__id',\n"
    "    'f_type':'document_type__id',\n"
    "    'f_path':'storage_path__id',\n"
    "    'f_tag':'tags__id__all'\n"
    "  };\n"
    "  for(var id in map){\n"
    "    var val=document.getElementById(id).value;\n"
    "    if(val) params.append(map[id],val);\n"
    "  }\n"
    "  var gte=document.getElementById('f_date_gte').value;\n"
    "  var lte=document.getElementById('f_date_lte').value;\n"
    "  if(gte) params.append(mode+'__date__gte',gte);\n"
    "  if(lte) params.append(mode+'__date__lte',lte);\n"
    "  try{\n"
    "    var firstResp=await fetch('/api/data?'+params.toString()+'&page=1');\n"
    "    if(!firstResp.ok) throw new Error('HTTP '+firstResp.status);\n"
    "    var firstData=await firstResp.json();\n"
    "    var total=firstData.count||0;\n"
    "    var pageSize=firstData.page_size||25;\n"
    "    var totalPages=Math.ceil(total/pageSize);\n"
    "    var allDocs=firstData.results||[];\n"
    "    bar.style.width=Math.round(100/Math.max(totalPages,1))+'%';\n"
    "    for(var page=2;page<=totalPages;page++){\n"
    "      st.textContent=tr.st_page+' '+page+' '+tr.st_of+' '+totalPages+'...';\n"
    "      var resp=await fetch('/api/data?'+params.toString()+'&page='+page);\n"
    "      if(!resp.ok) break;\n"
    "      var pd=await resp.json();\n"
    "      allDocs=allDocs.concat(pd.results||[]);\n"
    "      bar.style.width=Math.round((page/totalPages)*100)+'%';\n"
    "    }\n"
    "    var tbody=document.querySelector('#target tbody');\n"
    "    tbody.innerHTML='';\n"
    "    allDocs.forEach(function(d){\n"
    "      var row=document.createElement('tr');\n"
    "      var cols=[d.created,d.added,d.title,d.corr,d.tags,d.type,d.path,d.val];\n"
    "      cols.forEach(function(v,i){\n"
    "        var td=document.createElement('td');\n"
    "        td.className='c'+i;\n"
    "        td.title=v||'';\n"
    "        if(i===2){\n"
    "          var a=document.createElement('a');\n"
    "          a.href=d.link||'#';\n"
    "          a.target='_blank';\n"
    "          a.rel='noopener noreferrer';\n"
    "          a.textContent=v||'';\n"
    "          a.title=v||'';\n"
    "          td.appendChild(a);\n"
    "        } else {\n"
    "          td.textContent=v||'';\n"
    "        }\n"
    "        var thEl=document.querySelector('th.c'+i);\n"
    "        if(thEl&&thEl.classList.contains('hidden')) td.classList.add('hidden');\n"
    "        row.appendChild(td);\n"
    "      });\n"
    "      tbody.appendChild(row);\n"
    "    });\n"
    "    st.textContent=allDocs.length+' '+tr.st_done;\n"
    "  } catch(e){\n"
    "    st.className='status-error';\n"
    "    st.textContent=T[lang].st_error;\n"
    "    console.error(e);\n"
    "  } finally {\n"
    "    setTimeout(function(){wrap.style.display='none';bar.style.width='0%';},800);\n"
    "  }\n"
    "}\n"
    "window.loadDocs = loadDocs;\n"
    "\n"
    "/* CSV Export */\n"
    "function exportCSV(){\n"
    "  var tr=T[lang];\n"
    "  var csv=tr.col.map(function(h){return '\"'+h+'\"';}).join(';')+'\\n';\n"
    "  document.querySelectorAll('#target tbody tr').forEach(function(row){\n"
    "    csv+=Array.from(row.cells).map(function(c){\n"
    "      return '\"'+(c.textContent||'').replace(/\"/g,'\"\"')+'\"';\n"
    "    }).join(';')+'\\n';\n"
    "  });\n"
    "  var blob=new Blob(['\\uFEFF'+csv],{type:'text/csv;charset=utf-8;'});\n"
    "  var link=document.createElement('a');\n"
    "  link.href=URL.createObjectURL(blob);\n"
    "  link.download=tr.csv_file;\n"
    "  link.click();\n"
    "}\n"
    "window.exportCSV = exportCSV;\n"
    "\n"
    "/* Init */\n"
    "setLang(detectLang());\n"
    "if(!HAS_URL||!HAS_TOKEN){\n"
    "  document.getElementById('modal').style.display='flex';\n"
    "}\n"
    "\n"
    "})();\n"
    "</script>\n"
    "</body>\n"
    "</html>\n"
)


@app.route('/')
def index():
    conf = load_config()
    fetch_all_meta()
    html = render_template_string(HTML_TEMPLATE, meta=meta_cache['data'], conf=conf)
    return Response(html, content_type='text/html; charset=utf-8')


@app.route('/api/settings', methods=['POST'])
@limiter.limit("10 per minute")
def settings():
    data = request.json
    if not data:
        return jsonify({"status": "error", "msg": "No data"}), 400
    url   = data.get('url', '').strip()
    token = data.get('token', '').strip()
    if not url or not token:
        return jsonify({"status": "error", "msg": "URL and token required"}), 400
    if not (url.startswith('http://') or url.startswith('https://')):
        return jsonify({"status": "error", "msg": "Invalid URL scheme"}), 400
    save_config(url, token)
    meta_cache['last_fetch'] = 0
    return jsonify({"status": "ok"})


@app.route('/api/data')
@limiter.limit("30 per minute")
def get_data():
    conf = load_config()
    if not conf.get('url') or not conf.get('token'):
        return jsonify({"count": 0, "page_size": 25, "results": []})
    try:
        page = max(1, int(request.args.get('page', 1)))
    except ValueError:
        page = 1

    ALLOWED_PARAMS = {
        'query', 'correspondent__id', 'document_type__id',
        'storage_path__id', 'tags__id__all',
        'created__date__gte', 'created__date__lte',
        'added__date__gte',   'added__date__lte'
    }
    params = {}
    for k, v in request.args.to_dict().items():
        if k in ALLOWED_PARAMS and v.strip():
            params[k] = v.strip()
    params['page']      = page
    params['page_size'] = 25

    try:
        r = requests.get(
            conf['url'] + "/api/documents/",
            headers=get_headers(),
            params=params,
            timeout=15
        )
        if r.status_code == 401:
            return jsonify({"error": "unauthorized", "count": 0, "results": []}), 401
        if r.status_code != 200:
            return jsonify({"error": "upstream_" + str(r.status_code), "count": 0, "results": []}), 502

        raw     = r.json()
        count   = raw.get('count', 0)
        results = raw.get('results', [])
        output  = []

        for d in results:
            val = ""
            for cf in d.get('custom_fields', []):
                v = cf.get('value')
                if v is not None and str(v).strip():
                    val = str(v)
                    break
            doc_id = d.get('id', '')
            output.append({
                "id":      doc_id,
                "created": (d.get('created', '') or '').split('T')[0],
                "added":   (d.get('added',   '') or '').split('T')[0],
                "title":   d.get('title', ''),
                "corr":    meta_cache['data']['correspondents'].get(d.get('correspondent'), ""),
                "tags":    ", ".join(
                               meta_cache['data']['tags'].get(tg, "")
                               for tg in d.get('tags', [])
                           ),
                "type":    meta_cache['data']['document_types'].get(d.get('document_type'), ""),
                "path":    meta_cache['data']['storage_paths'].get(d.get('storage_path'), ""),
                "val":     val,
                "link":    conf['url'] + "/documents/" + str(doc_id) if doc_id else ""
            })

        return jsonify({"count": count, "page_size": 25, "results": output})

    except requests.exceptions.ConnectionError:
        return jsonify({"error": "connection_error", "count": 0, "results": []}), 502
    except requests.exceptions.Timeout:
        return jsonify({"error": "timeout", "count": 0, "results": []}), 504
    except Exception as e:
        print("Fehler: " + str(e))
        return jsonify({"error": "unknown", "count": 0, "results": []}), 500


@app.route('/api/meta/refresh', methods=['POST'])
@limiter.limit("5 per minute")
def refresh_meta():
    fetch_all_meta(force=True)
    return jsonify({"status": "ok"})


if __name__ == '__main__':
    os.makedirs('/data', exist_ok=True)
    app.run(host='0.0.0.0', port=5001, debug=False)
