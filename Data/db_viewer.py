from flask import Flask, render_template_string, request, jsonify
import sqlite3
from pathlib import Path

app = Flask(__name__)

DB_PATH = Path(__file__).resolve().parent / "investors.db"


# ============================================================
# DATABASE
# ============================================================

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_tables():
    conn = get_connection()

    tables = conn.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
    """).fetchall()

    conn.close()

    return [row["name"] for row in tables]


def get_columns(table):
    conn = get_connection()

    columns = conn.execute(
        f'PRAGMA table_info("{table}")'
    ).fetchall()

    conn.close()

    return [row["name"] for row in columns]


def get_data(table):
    conn = get_connection()

    rows = conn.execute(
        f'SELECT * FROM "{table}"'
    ).fetchall()

    conn.close()

    return [dict(row) for row in rows]


# ============================================================
# API
# ============================================================

@app.route("/api/tables")
def api_tables():
    return jsonify(get_tables())


@app.route("/api/data")
def api_data():

    table = request.args.get("table")

    if not table:
        return jsonify({
            "error": "No table specified"
        }), 400

    tables = get_tables()

    if table not in tables:
        return jsonify({
            "error": "Invalid table"
        }), 400

    columns = get_columns(table)
    rows = get_data(table)

    return jsonify({
        "columns": columns,
        "rows": rows
    })


# ============================================================
# WEB PAGE
# ============================================================

HTML = """
<!DOCTYPE html>

<html>

<head>

    <title>Conflux DB Viewer</title>

    <meta name="viewport"
          content="width=device-width, initial-scale=1">

    <style>

        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            background: #111318;
            color: #e8e8e8;
            font-family: Arial, sans-serif;
        }

        .header {
            padding: 18px 24px;
            background: #191c23;
            border-bottom: 1px solid #292d36;
        }

        .header h1 {
            margin: 0;
            font-size: 22px;
        }

        .header p {
            margin: 5px 0 0;
            color: #888f9d;
            font-size: 13px;
        }

        .controls {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            padding: 15px 20px;
            background: #171a20;
            border-bottom: 1px solid #292d36;
        }

        select,
        input,
        button {
            background: #222630;
            color: #eee;
            border: 1px solid #353a46;
            border-radius: 6px;
            padding: 9px 12px;
            font-size: 14px;
        }

        select:focus,
        input:focus {
            outline: none;
            border-color: #667cff;
        }

        input {
            min-width: 250px;
        }

        button {
            cursor: pointer;
        }

        button:hover {
            background: #2b303c;
        }

        .stats {
            padding: 10px 20px;
            color: #858c99;
            font-size: 13px;
        }

        .table-container {
            overflow: auto;
            height: calc(100vh - 150px);
        }

        table {
            border-collapse: collapse;
            width: max-content;
            min-width: 100%;
        }

        th {
            position: sticky;
            top: 0;
            background: #20242d;
            color: #cfd4df;
            cursor: pointer;
            user-select: none;
            text-align: left;
            padding: 11px 14px;
            border-bottom: 1px solid #363b46;
            white-space: nowrap;
        }

        th:hover {
            background: #292e39;
        }

        td {
            padding: 9px 14px;
            border-bottom: 1px solid #22262e;
            white-space: nowrap;
            max-width: 500px;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        tr:hover td {
            background: #1b1f27;
        }

        .positive {
            color: #62d98a;
        }

        .negative {
            color: #ff7070;
        }

        .empty {
            padding: 40px;
            text-align: center;
            color: #777;
        }

    </style>

</head>


<body>

    <div class="header">

        <h1>Conflux DB Viewer</h1>

        <p>
            SQLite Database Viewer
        </p>

    </div>


    <div class="controls">

        <select id="tableSelect"
                onchange="loadData()">
        </select>


        <input
            id="search"
            type="text"
            placeholder="Search..."
            oninput="renderTable()"
        >


        <select id="sortSelect"
                onchange="renderTable()">
        </select>


        <select id="direction"
                onchange="renderTable()">

            <option value="desc">
                Descending
            </option>

            <option value="asc">
                Ascending
            </option>

        </select>


        <button onclick="loadData()">
            Refresh
        </button>

    </div>


    <div class="stats"
         id="stats">
    </div>


    <div class="table-container">

        <table>

            <thead id="tableHead">
            </thead>

            <tbody id="tableBody">
            </tbody>

        </table>

    </div>


<script>

let columns = [];
let rows = [];


// ============================================================
// LOAD TABLES
// ============================================================

async function loadTables() {

    const response =
        await fetch("/api/tables");

    const tables =
        await response.json();

    const select =
        document.getElementById("tableSelect");

    select.innerHTML = "";

    tables.forEach(table => {

        const option =
            document.createElement("option");

        option.value = table;
        option.textContent = table;

        select.appendChild(option);

    });

    if (tables.length > 0) {
        loadData();
    }
}


// ============================================================
// LOAD DATA
// ============================================================

async function loadData() {

    const table =
        document.getElementById("tableSelect").value;

    if (!table)
        return;

    const response =
        await fetch(
            "/api/data?table="
            + encodeURIComponent(table)
        );

    const data =
        await response.json();

    columns = data.columns;
    rows = data.rows;

    updateSortDropdown();

    renderTable();
}


// ============================================================
// SORT DROPDOWN
// ============================================================

function updateSortDropdown() {

    const select =
        document.getElementById("sortSelect");

    const previous =
        select.value;

    select.innerHTML = "";

    columns.forEach(column => {

        const option =
            document.createElement("option");

        option.value = column;
        option.textContent = column;

        select.appendChild(option);

    });

    if (columns.includes(previous)) {

        select.value = previous;

    } else if (columns.length > 0) {

        select.value = columns[0];

    }
}


// ============================================================
// RENDER
// ============================================================

function renderTable() {

    const head =
        document.getElementById("tableHead");

    const body =
        document.getElementById("tableBody");

    const search =
        document.getElementById("search")
            .value
            .toLowerCase();

    const sortColumn =
        document.getElementById("sortSelect")
            .value;

    const direction =
        document.getElementById("direction")
            .value;

    // --------------------------------------------------------
    // Filter
    // --------------------------------------------------------

    let filtered =
        rows.filter(row => {

            if (!search)
                return true;

            return columns.some(column => {

                const value =
                    row[column];

                return String(value ?? "")
                    .toLowerCase()
                    .includes(search);

            });

        });


    // --------------------------------------------------------
    // Sort
    // --------------------------------------------------------

    filtered.sort((a, b) => {

        const av = a[sortColumn];
        const bv = b[sortColumn];

        if (av == null)
            return -1;

        if (bv == null)
            return 1;

        const an = Number(av);
        const bn = Number(bv);

        let result;

        if (!isNaN(an) && !isNaN(bn)) {

            result = an - bn;

        } else {

            result =
                String(av)
                    .localeCompare(
                        String(bv),
                        undefined,
                        {
                            numeric: true,
                            sensitivity: "base"
                        }
                    );

        }

        return direction === "asc"
            ? result
            : -result;

    });


    // --------------------------------------------------------
    // Headers
    // --------------------------------------------------------

    head.innerHTML = "";

    const headerRow =
        document.createElement("tr");

    columns.forEach(column => {

        const th =
            document.createElement("th");

        th.textContent = column;

        th.onclick = () => {

            document.getElementById(
                "sortSelect"
            ).value = column;

            renderTable();

        };

        headerRow.appendChild(th);

    });

    head.appendChild(headerRow);


    // --------------------------------------------------------
    // Rows
    // --------------------------------------------------------

    body.innerHTML = "";

    filtered.forEach(row => {

        const tr =
            document.createElement("tr");

        columns.forEach(column => {

            const td =
                document.createElement("td");

            const value =
                row[column];

            td.textContent =
                value == null
                    ? ""
                    : value;

            tr.appendChild(td);

        });

        body.appendChild(tr);

    });


    // --------------------------------------------------------
    // Stats
    // --------------------------------------------------------

    document.getElementById("stats")
        .textContent =
        `${filtered.length} / ${rows.length} rows`;

}


// ============================================================
// START
// ============================================================

loadTables();

</script>

</body>

</html>
"""


# ============================================================
# PAGE ROUTE
# ============================================================

@app.route("/")
def index():
    return render_template_string(HTML)


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 50)
    print("        CONFLUX DATABASE VIEWER")
    print("=" * 50)
    print()
    print(f"Database: {DB_PATH}")
    print()
    print("Local:   http://localhost:5000")
    print()
    print("Press CTRL+C to stop")
    print()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )