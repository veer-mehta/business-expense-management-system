from flask import Flask, render_template, request, redirect, url_for, flash
import MySQLdb
from MySQLdb import cursors
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")


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
        pass

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
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SHOW TABLES")
    tables = [row[0] for row in cursor.fetchall()]
    
    # Get selected table
    if request.method == 'POST':
        selected_table = request.form.get("select_table") or request.form.get("selected_table")
    else:
        selected_table = request.args.get("select_table") or request.args.get("selected_table")
    
    if not selected_table:
        selected_table = tables[0]
    
    # Get table columns
    columns = get_table_columns(cursor, selected_table)
    enum_fields = get_enum_fields(cursor, selected_table)
    auto_inc_fields = get_auto_increment_fields(cursor, selected_table)
    
    # Search functionality
    search_query = request.args.get('search', '')
    search_column = request.args.get('search_column', '')
    
    # Sorting parameters
    sort_column = request.args.get('sort', columns[0] if columns else '')
    sort_direction = request.args.get('direction', 'asc')
    
    
    # Build the query
    query = f"SELECT * FROM {selected_table}"
    count_query = f"SELECT COUNT(*) FROM {selected_table}"
    params = []
    
    # Add search condition if provided
    if search_query and search_column and search_column in columns:
        query += f" WHERE {search_column} LIKE %s"
        count_query += f" WHERE {search_column} LIKE %s"
        params.append(f"%{search_query}%")
    
    # Add sorting if provided
    if sort_column and sort_column in columns:
        query += f" ORDER BY {sort_column} {'ASC' if sort_direction.lower() == 'asc' else 'DESC'}"
    
    # Execute the final query
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    edt_row = request.args.get("edit_row", None)
    
    return render_template(
        'index.html',
        tables=tables,
        selected_table=selected_table,
        columns=columns,
        rows=rows,
        enum_fields=enum_fields,
        auto_inc_fields=auto_inc_fields,
        edt_row=int(edt_row) if edt_row else None,
        # Search data
        search_query=search_query,
        search_column=search_column,
        # Sort data
        sort_column=sort_column,
        sort_direction=sort_direction
    )

@app.route('/add', methods=['POST'])
def add_record():
    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get form data
        form_data = request.form.to_dict()
        selected_table = form_data.get('selected_table')
        
        # Capture search and sort params before removing
        search_query = form_data.get('search', '')
        search_column = form_data.get('search_column', '')
        sort_column = form_data.get('sort', '')
        sort_direction = form_data.get('direction', 'asc')
        
        # Remove non-table data from form
        form_data.pop('selected_table', None)
        form_data.pop('search', None)
        form_data.pop('search_column', None)
        form_data.pop('sort', None)
        form_data.pop('direction', None)
        
        if not selected_table:
            flash("No table selected", "error")
            return redirect(url_for('index'))
        
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
        flash(f"Failed to add record: {e}", "error")
    finally:
        if db:
            db.close()
    
    return redirect(url_for('index', 
                           select_table=selected_table,
                           search=search_query,
                           search_column=search_column,
                           sort=sort_column,
                           direction=sort_direction))

@app.route('/edit/<int:row_id>', methods=['POST'])
def edit_record(row_id):
    selected_table = request.form.get('selected_table') or request.form.get('select_table')
    if not selected_table:
        flash("No table selected", "error")
        return redirect(url_for('index'))
    
    # Preserve search and sort parameters
    search_query = request.form.get('search', '')
    search_column = request.form.get('search_column', '')
    sort_column = request.form.get('sort', '')
    sort_direction = request.form.get('direction', 'asc')
    
    return redirect(url_for('index', 
                           edit_row=row_id, 
                           select_table=selected_table,
                           search=search_query,
                           search_column=search_column,
                           sort=sort_column,
                           direction=sort_direction))

@app.route('/save/<int:row_id>', methods=['POST'])
def save_record(row_id):
    db = None
    try:
        db = get_db()
        cursor = db.cursor()

        # Get form data
        form_data = request.form.to_dict()
        selected_table = form_data.get('selected_table')
        
        # Capture search and sort params before removing
        search_query = form_data.get('search', '')
        search_column = form_data.get('search_column', '')
        sort_column = form_data.get('sort', '')
        sort_direction = form_data.get('direction', 'asc')
        
        # Remove non-table data from form
        form_data.pop('selected_table', None)
        form_data.pop('search', None)
        form_data.pop('search_column', None)
        form_data.pop('sort', None)
        form_data.pop('direction', None)
        
        if not selected_table:
            flash("No table selected", "error")
            return redirect(url_for('index'))
        
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
        flash(f"Failed to update record: {e}", "error")
    finally:
        if db:
            db.close()
    
    return redirect(url_for('index', 
                           select_table=selected_table,
                           search=search_query,
                           search_column=search_column,
                           sort=sort_column,
                           direction=sort_direction))

@app.route('/delete/<int:row_id>', methods=['POST'])
def delete_record(row_id):
    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get selected table from form data
        selected_table = request.form.get('selected_table')
        
        # Preserve search and sort parameters
        search_query = request.form.get('search', '')
        search_column = request.form.get('search_column', '')
        sort_column = request.form.get('sort', '')
        sort_direction = request.form.get('direction', 'asc')
        
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
        flash(f"Failed to delete record: {e}", "error")
    finally:
        if db:
            db.close()
    
    return redirect(url_for('index', 
                           select_table=selected_table,
                           search=search_query,
                           search_column=search_column,
                           sort=sort_column,
                           direction=sort_direction))
if __name__ == '__main__':
    app.run(debug=True)