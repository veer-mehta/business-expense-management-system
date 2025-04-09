from flask import Flask, render_template, request, redirect, url_for, flash
import MySQLdb
from MySQLdb import cursors
from dotenv import load_dotenv
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    filename='app.log')
logger = logging.getLogger('bems')

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "default_secret_key")

load_dotenv()

# Database connection function with error handling
def get_db():
    try:
        connection_timeout = 10
        connection = MySQLdb.connect(
            charset="utf8mb4",
            connect_timeout=connection_timeout,
            db=os.getenv("DB_NAME"),
            host=os.getenv("DB_HOST"),
            password=os.getenv("DB_PASS"),
            read_timeout=connection_timeout,
            port=int(os.getenv("DB_PORT", "3306")),
            user=os.getenv("DB_USER"),
            write_timeout=connection_timeout
        )
        return connection
    except MySQLdb.Error as e:
        logger.error(f"Database connection error: {e}")
        raise

# Helper functions
def get_table_columns(cursor, table_name):
    cursor.execute(f"SHOW COLUMNS FROM {table_name}")
    return [col[0] for col in cursor.fetchall()]

def get_enum_fields(cursor, table_name):
    cursor.execute(f"SHOW COLUMNS FROM {table_name}")
    enum_fields = {}
    for col in cursor.fetchall():
        col_name, col_type = col[0], col[1]
        if col_type.startswith("enum"):
            # Extract enum values more robustly
            enum_str = col_type[5:-1]  # Remove 'enum(' and ')'
            values = []
            current = ""
            in_quote = False
            
            for char in enum_str:
                if char == "'" and (not in_quote or current == ""):
                    in_quote = True
                elif char == "'" and in_quote:
                    in_quote = False
                    values.append(current)
                    current = ""
                elif in_quote:
                    current += char
            
            enum_fields[col_name] = values
    return enum_fields

def get_auto_increment_fields(cursor, table_name):
    cursor.execute(f"SHOW COLUMNS FROM {table_name}")
    return [col[0] for col in cursor.fetchall() if "auto_increment" in col[5].lower()]

@app.route('/', methods=['GET', 'POST'])
def index():
    try:
        db = get_db()
        cursor = db.cursor()

        # Get list of tables
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        
        if not tables:
            flash("No tables found in the database", "error")
            return render_template('index.html', tables=[], rows=[])
        
        # Get selected table from form OR query parameters
        selected_table = None
        if request.method == 'POST':
            selected_table = request.form.get("selected_table")
        else:
            # Check for selected_table in query parameters first
            selected_table = request.args.get("selected_table")
        
        # Default to first table if none selected
        if not selected_table and tables:
            selected_table = tables[0]        
        # Get column information
        columns = get_table_columns(cursor, selected_table)
        enum_fields = get_enum_fields(cursor, selected_table)
        auto_inc_fields = get_auto_increment_fields(cursor, selected_table)

        # Get table data
        cursor.execute(f"SELECT * FROM {selected_table}")
        rows = cursor.fetchall()

        # Get edit row (if any)
        edt_row = request.args.get("edit_row", None)

        return render_template(
            'index.html',
            tables=tables,
            selected_table=selected_table,
            columns=columns,
            rows=rows,
            enum_fields=enum_fields,
            auto_inc_fields=auto_inc_fields,
            edt_row=int(edt_row) if edt_row else None
        )
    except Exception as e:
        logger.error(f"Error in index route: {e}")
        flash(f"An error occurred: {e}", "error")
        return render_template('index.html', tables=[], rows=[])
    finally:
        if 'db' in locals():
            db.close()

@app.route('/add', methods=['POST'])
def add_record():
    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get form data
        form_data = request.form.to_dict()
        selected_table = form_data.get('selected_table')
        
        if not selected_table:
            flash("No table selected", "error")
            return redirect(url_for('index'))
        
        # Remove selected_table from form data
        form_data.pop('selected_table', None)
        
        # Get columns and values
        columns = list(form_data.keys())
        values = list(form_data.values())
        
        if not columns:
            flash("No data provided", "error")
            return redirect(url_for('index'))
        
        # Build and execute query
        placeholders = ", ".join(["%s"] * len(values))
        col_names = ", ".join(columns)
        
        cursor.execute(f"INSERT INTO {selected_table} ({col_names}) VALUES ({placeholders})", values)
        db.commit()
        flash("Record added successfully!", "success")
    except Exception as e:
        if db:
            db.rollback()
        logger.error(f"Error adding record: {e}")
        flash(f"Failed to add record: {e}", "error")
    finally:
        if db:
            db.close()
    
    return redirect(url_for('index'))

@app.route('/edit/<int:row_id>', methods=['POST'])
def edit_record(row_id):
    selected_table = request.form.get('selected_table')
    if not selected_table:
        flash("No table selected", "error")
    return redirect(url_for('index', edit_row=row_id, selected_table=selected_table))

@app.route('/save/<int:row_id>', methods=['POST'])
def save_record(row_id):
    db = None
    try:
        db = get_db()
        cursor = db.cursor()

        # Get form data
        form_data = request.form.to_dict()
        selected_table = form_data.get('selected_table')
        
        if not selected_table:
            flash("No table selected", "error")
            return redirect(url_for('index'))
        
        # Remove selected_table from form data
        form_data.pop('selected_table', None)
        
        # Get primary key column
        cursor.execute(f"SHOW COLUMNS FROM {selected_table}")
        columns = cursor.fetchall()
        primary_key = columns[0][0]  # Assuming first column is primary key
        
        # Build and execute query
        set_clause = ", ".join([f"{col}=%s" for col in form_data.keys()])
        values = list(form_data.values()) + [row_id]
        
        cursor.execute(f"UPDATE {selected_table} SET {set_clause} WHERE {primary_key}=%s", values)
        db.commit()
        flash("Record updated successfully!", "success")
    except Exception as e:
        if db:
            db.rollback()
        logger.error(f"Error updating record: {e}")
        flash(f"Failed to update record: {e}", "error")
    finally:
        if db:
            db.close()
    
    return redirect(url_for('index'))

@app.route('/delete/<int:row_id>', methods=['POST'])
def delete_record(row_id):
    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get selected table from form data
        selected_table = request.form.get('selected_table')
        
        if not selected_table:
            flash("No table selected", "error")
            return redirect(url_for('index'))
        
        # Get primary key column
        cursor.execute(f"SHOW COLUMNS FROM {selected_table}")
        columns = cursor.fetchall()
        primary_key = columns[0][0]  # Assuming first column is primary key
        
        # Execute delete query
        cursor.execute(f"DELETE FROM {selected_table} WHERE {primary_key} = %s", (row_id,))
        db.commit()
        flash("Record deleted successfully!", "success")
    except Exception as e:
        if db:
            db.rollback()
        logger.error(f"Error deleting record: {e}")
        flash(f"Failed to delete record: {e}", "error")
    finally:
        if db:
            db.close()
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)