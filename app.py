from flask import Flask, render_template, request, redirect, url_for
import MySQLdb
from dotenv import load_dotenv
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = "SECRET_KEY"

load_dotenv()

t = 10
db = MySQLdb.connect(
  charset="utf8mb4",
  connect_timeout=t,
  db=os.getenv("DB_NAME"),
  host=os.getenv("DB_HOST"),
  password=os.getenv("DB_PASS"),
  read_timeout=t,
  port=14898,
  user=os.getenv("DB_USER"),
  write_timeout=t,
)
csr = db.cursor()
edt_row = None
selected_table = "Users"

def get_table_names():
	csr.execute("SHOW TABLES")
	return [row[0] for row in csr.fetchall()]

def get_primary_key(table):
	csr.execute(f"SHOW KEYS FROM `{table}` WHERE Key_name = 'PRIMARY'")
	result = csr.fetchone()
	return result[4] if result else None

@app.route("/", methods=["GET", "POST"])
def dsp():
	global selected_table, edt_row
	tables = get_table_names()

	if request.method == "POST" and "table_select" in request.form:
		selected_table = request.form["table_select"]
		edt_row = None

	# Fetch column info (only once)
	csr.execute(f"SHOW COLUMNS FROM `{selected_table}`")
	raw_cols = csr.fetchall()

	columns = [col[0].replace('_', ' ').title() for col in raw_cols]

	# Detect ENUM fields and values
	enum_fields = {}
	auto_inc_fields = set()

	for col in raw_cols:
		field_raw = col[0]
		field_display = field_raw.replace('_', ' ').title()
		col_type = col[1]
		extra = col[5]

		if col_type.startswith("enum"):
			values = col_type.strip("enum()")
			values = [v.strip("'") for v in values.split(",")]
			enum_fields[field_display] = values

		if col_type.startswith("timestamp"):
			auto_inc_fields.add(field_display)

		if "auto_increment" in extra.lower() or "timestamp" in extra.lower():
			auto_inc_fields.add(field_display)

	# Fetch all rows from selected table
	csr.execute(f"SELECT * FROM `{selected_table}`")
	rows = csr.fetchall()

	# Get primary key
	pk = get_primary_key(selected_table).replace('_', ' ').title()

	return render_template(
		"index.html",
		tables=tables,
		selected_table=selected_table,
		columns=columns,
		rows=rows,
		pk=pk,
		edt_row=edt_row,
		enum_fields=enum_fields,
		auto_inc_fields=auto_inc_fields
	)

@app.route("/edit/<pkval>", methods=["POST"])
def edt(pkval):
	global edt_row
	edt_row = pkval
	return redirect(url_for("dsp"))

@app.route("/save/<pkval>", methods=["POST"])
def sav(pkval):
	global edt_row
	csr.execute(f"SHOW COLUMNS FROM `{selected_table}`")
	columns = [col[0] for col in csr.fetchall()]
	pk = get_primary_key(selected_table)

	values = [request.form.get(col) for col in columns if col != pk]
	update_cols = [f"{col}=%s" for col in columns if col != pk]

	query = f"UPDATE `{selected_table}` SET {', '.join(update_cols)} WHERE `{pk}` = %s"
	csr.execute(query, (*values, pkval))
	db.commit()
	edt_row = None
	return redirect(url_for("dsp"))

@app.route("/delete/<pkval>", methods=["POST"])
def dlt(pkval):
	pk = get_primary_key(selected_table)
	csr.execute(f"DELETE FROM `{selected_table}` WHERE `{pk}` = %s", (pkval,))
	db.commit()
	return redirect(url_for("dsp"))

@app.route("/add", methods=["POST"])
def add():
	csr.execute(f"SHOW COLUMNS FROM `{selected_table}`")
	columns = [col[0] for col in csr.fetchall()]
	pk = get_primary_key(selected_table)


	insert_cols = [col for col in columns if col != pk]
	values = [request.form.get(col.replace('_', ' ').title()) for col in insert_cols]
	placeholders = ", ".join(["%s"] * len(values))

	query = f"INSERT INTO `{selected_table}` ({', '.join(insert_cols)}) VALUES ({placeholders})"
	#open("log.txt", 'a').write("Q:"+str(query)+"\nIC: "+str(insert_cols)+"\nC: "+str(columns)+"\nV: "+str(values)+"\n")
	csr.execute(query, values)
	db.commit()
	return redirect(url_for("dsp"))
