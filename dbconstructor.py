import MySQLdb
import load_dotenv from dotenv
import os

load_dotenv()

timeout = 10
connection = MySQLdb.connect(
  charset="utf8mb4",
  connect_timeout=timeout,
  db=os.getenv("DB_NAME"),
  host=os.getenv("DB_HOST"),
  password=os.getenv("DB_PASS"),
  read_timeout=timeout,
  port=14898,
  user=os.getenv("DB_USER"),
  write_timeout=timeout,
)

cursor = connection.cursor()  

def create_db():
	cursor.execute("""
	CREATE TABLE IF NOT EXISTS Departments (
		department_id INT PRIMARY KEY AUTO_INCREMENT,
		name VARCHAR(100) UNIQUE,
		budget_limit DECIMAL(12,2),
		manager_id INT
	);""")

	cursor.execute("""
	CREATE TABLE IF NOT EXISTS Users (
		user_id INT PRIMARY KEY AUTO_INCREMENT,
		first_name VARCHAR(50),
		last_name VARCHAR(50),
		email VARCHAR(100) UNIQUE,
		password_hash VARCHAR(255),
		role ENUM('employee', 'manager', 'admin'),
		department_id INT,
		created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
	);
	""")

	cursor.execute("""
	CREATE TABLE IF NOT EXISTS Expense_Categories (
		category_id INT PRIMARY KEY AUTO_INCREMENT,
		category_name VARCHAR(100) UNIQUE,
		description TEXT
	);
	""")

	cursor.execute("""
	CREATE TABLE IF NOT EXISTS Expenses (
		expense_id INT PRIMARY KEY AUTO_INCREMENT,
		user_id INT,
		category_id INT,
		amount DECIMAL(12,2),
		description TEXT,
		expense_date DATE,
		status ENUM('pending', 'approved', 'rejected'),
		approved_by INT NULL,
		created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
	);
	""")

	cursor.execute("""
	CREATE TABLE IF NOT EXISTS Expense_Approval (
		approval_id INT PRIMARY KEY AUTO_INCREMENT,
		expense_id INT,
		manager_id INT,
		approval_status ENUM('approved', 'rejected'),
		approval_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
	);
	""")

	cursor.execute("""
	CREATE TABLE IF NOT EXISTS Payment_Methods (
		payment_method_id INT PRIMARY KEY AUTO_INCREMENT,
		method_name VARCHAR(50) UNIQUE,
		description TEXT
	);
	""")

	cursor.execute("""
	CREATE TABLE IF NOT EXISTS Expense_Payments (
		payment_id INT PRIMARY KEY AUTO_INCREMENT,
		expense_id INT,
		payment_method_id INT,
		paid_amount DECIMAL(12,2),
		payment_date DATE,
		transaction_reference VARCHAR(100) UNIQUE,
		status ENUM('completed', 'failed')
	);
	""")

	cursor.execute("""
	CREATE TABLE IF NOT EXISTS Vendors (
		vendor_id INT PRIMARY KEY AUTO_INCREMENT,
		vendor_name VARCHAR(100) UNIQUE,
		contact_person VARCHAR(100),
		contact_email VARCHAR(100) UNIQUE,
		contact_phone VARCHAR(15),
		address TEXT
	);
	""")

	cursor.execute("""
	CREATE TABLE IF NOT EXISTS Expense_Attachments (
		attachment_id INT PRIMARY KEY AUTO_INCREMENT,
		expense_id INT,
		file_path VARCHAR(255),
		uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
	);
	""")

	cursor.execute("""
	CREATE TABLE IF NOT EXISTS Audit_Log (
		log_id INT PRIMARY KEY AUTO_INCREMENT,
		user_id INT,
		action_type VARCHAR(100),
		action_description TEXT,
		action_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
	);
	""")


	cursor.execute("""
	ALTER TABLE Users
	ADD CONSTRAINT fk_users_department FOREIGN KEY (department_id) 
	REFERENCES Departments(department_id);
	""")

	cursor.execute("""
	ALTER TABLE Departments
	ADD CONSTRAINT fk_departments_manager FOREIGN KEY (manager_id) 
	REFERENCES Users(user_id);
	""")

	cursor.execute("""
	ALTER TABLE Expenses
	ADD CONSTRAINT fk_expenses_user FOREIGN KEY (user_id) 
	REFERENCES Users(user_id),
	ADD CONSTRAINT fk_expenses_category FOREIGN KEY (category_id) 
	REFERENCES Expense_Categories(category_id),
	ADD CONSTRAINT fk_expenses_approved_by FOREIGN KEY (approved_by) 
	REFERENCES Users(user_id);
	""")

	cursor.execute("""
	ALTER TABLE Expense_Approval
	ADD CONSTRAINT fk_approval_expense FOREIGN KEY (expense_id) 
	REFERENCES Expenses(expense_id),
	ADD CONSTRAINT fk_approval_manager FOREIGN KEY (manager_id) 
	REFERENCES Users(user_id);
	""")

	cursor.execute("""
	ALTER TABLE Expense_Payments
	ADD CONSTRAINT fk_payments_expense FOREIGN KEY (expense_id) 
	REFERENCES Expenses(expense_id),
	ADD CONSTRAINT fk_payments_method FOREIGN KEY (payment_method_id) 
	REFERENCES Payment_Methods(payment_method_id);
	""")

	cursor.execute("""
	ALTER TABLE Expense_Attachments
	ADD CONSTRAINT fk_attachments_expense FOREIGN KEY (expense_id) 
	REFERENCES Expenses(expense_id);
	""")

	cursor.execute("""
	ALTER TABLE Audit_Log
	ADD CONSTRAINT fk_audit_user FOREIGN KEY (user_id) 
	REFERENCES Users(user_id);
	""")
	


create_db()