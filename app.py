from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Khóa bí mật để sử dụng session

# Hàm kết nối cơ sở dữ liệu
def get_db_connection():
    conn = sqlite3.connect('store.db')
    conn.row_factory = sqlite3.Row
    return conn

# Khởi tạo cơ sở dữ liệu
def initialize_db():
    conn = get_db_connection()
    with conn:
        # Tạo bảng sản phẩm nếu chưa tồn tại
        conn.execute('''CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                price REAL NOT NULL,
                quantity INTEGER NOT NULL,
                user_id INTEGER NOT NULL
            );''')

        # Tạo bảng khách hàng
        conn.execute('''CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                address TEXT NOT NULL,
                user_id INTEGER NOT NULL
            );''')

        # Tạo bảng hóa đơn
        conn.execute('''CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                total_price REAL NOT NULL,
                date TEXT NOT NULL,
                user_id INTEGER NOT NULL
            );''')

        # Tạo bảng người dùng
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            );''')

        
    conn.close()

# Đăng ký người dùng
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
            flash('Đăng ký thành công! Bạn có thể đăng nhập ngay.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Tên người dùng đã tồn tại! Vui lòng chọn tên khác.')
        finally:
            conn.close()
    
    return render_template('signup.html')

# Đăng nhập người dùng
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
        conn.close()

        if user:
            session['username'] = user['username']
            session['user_id'] = user['id']  # Lưu user_id vào session
            flash('Đăng nhập thành công!')
            return redirect(url_for('index'))
        else:
            flash('Tên đăng nhập hoặc mật khẩu không đúng!')

    return render_template('login.html')

# Đăng xuất
@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('user_id', None)  # Xóa user_id khỏi session
    flash('Bạn đã đăng xuất thành công!')
    return redirect(url_for('index'))

# Trang chủ
@app.route('/')
def index():
    return render_template('index.html')

# Quản lý sản phẩm (hiển thị và thêm sản phẩm)
@app.route('/products', methods=['GET', 'POST'])
def products():
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập để xem sản phẩm.')
        return redirect(url_for('login'))

    conn = get_db_connection()
    
    # Tìm kiếm sản phẩm
    search_query = request.args.get('search')
    if search_query:
        products = conn.execute('SELECT * FROM products WHERE name LIKE ? AND user_id = ?',
                                ('%' + search_query + '%', session['user_id'])).fetchall()
    else:
        products = conn.execute('SELECT * FROM products WHERE user_id = ?', (session['user_id'],)).fetchall()

    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        price = request.form['price']
        quantity = request.form['quantity']
        conn.execute('INSERT INTO products (name, category, price, quantity, user_id) VALUES (?, ?, ?, ?, ?) ',
                     (name, category, price, quantity, session['user_id']))
        conn.commit()
        flash('Sản phẩm đã được thêm thành công!')
        return redirect(url_for('products'))

    conn.close()
    return render_template('products.html', products=products)

# Chỉnh sửa sản phẩm
@app.route('/products/edit/<int:id>', methods=['GET', 'POST'])
def edit_product(id):
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập để chỉnh sửa sản phẩm.')
        return redirect(url_for('login'))

    conn = get_db_connection()
    product = conn.execute('SELECT * FROM products WHERE id = ? AND user_id = ?', (id, session['user_id'])).fetchone()

    if not product:
        flash('Sản phẩm không tồn tại hoặc không thuộc về bạn.')
        return redirect(url_for('products'))

    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        price = request.form['price']
        quantity = request.form['quantity']
        
        # Kiểm tra các trường dữ liệu trước khi cập nhật
        if not name or not category or not price or not quantity:
            flash('Vui lòng điền đầy đủ thông tin sản phẩm.')
            return redirect(url_for('edit_product', id=id))

        conn.execute('UPDATE products SET name = ?, category = ?, price = ?, quantity = ? WHERE id = ?',
                     (name, category, price, quantity, id))
        conn.commit()
        flash('Sản phẩm đã được cập nhật thành công!')
        return redirect(url_for('products'))

    conn.close()
    return render_template('edit_product.html', product=product)

@app.route('/products/delete/<int:id>', methods=['POST'])
def delete_product(id):
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập để xóa sản phẩm.')
        return redirect(url_for('login'))

    conn = get_db_connection()
    product = conn.execute('SELECT * FROM products WHERE id = ? AND user_id = ?', (id, session['user_id'])).fetchone()
    
    if not product:
        flash('Không tìm thấy sản phẩm hoặc sản phẩm không thuộc về bạn.')
        return redirect(url_for('products'))

    conn.execute('DELETE FROM products WHERE id = ? AND user_id = ?', (id, session['user_id']))
    conn.commit()
    flash('Sản phẩm đã được xóa thành công!')
    return redirect(url_for('products'))



# Quản lý khách hàng (hiển thị và thêm khách hàng)
@app.route('/customers', methods=['GET', 'POST'])
def customers():
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập để xem khách hàng.')
        return redirect(url_for('login'))

    conn = get_db_connection()
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        address = request.form['address']
        conn.execute('INSERT INTO customers (name, phone, address, user_id) VALUES (?, ?, ?, ?)',
                     (name, phone, address, session['user_id']))
        conn.commit()
        flash('Khách hàng đã được thêm thành công!')
        return redirect(url_for('customers'))

    customers = conn.execute('SELECT * FROM customers WHERE user_id = ?', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('customers.html', customers=customers)

# Chỉnh sửa khách hàng
@app.route('/customers/edit/<int:id>', methods=['GET', 'POST'])
def edit_customer(id):
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập để chỉnh sửa khách hàng.')
        return redirect(url_for('login'))

    conn = get_db_connection()
    customer = conn.execute('SELECT * FROM customers WHERE id = ? AND user_id = ?', (id, session['user_id'])).fetchone()

    if not customer:
        flash('Khách hàng không tồn tại.')
        return redirect(url_for('customers'))

    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        address = request.form['address']
        conn.execute('UPDATE customers SET name = ?, phone = ?, address = ? WHERE id = ?',
                     (name, phone, address, id))
        conn.commit()
        flash('Khách hàng đã được cập nhật thành công!')
        return redirect(url_for('customers'))

    conn.close()
    return render_template('edit_customer.html', customer=customer)

@app.route('/customers/delete/<int:id>', methods=['POST'])
def delete_customer(id):
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập để xóa khách hàng.')
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute('DELETE FROM customers WHERE id = ? AND user_id = ?', (id, session['user_id']))
    conn.commit()
    flash('Khách hàng đã được xóa thành công!')
    return redirect(url_for('customers'))


@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập để thêm sản phẩm vào giỏ hàng.')
        return redirect(url_for('login'))

    # Kiểm tra xem 'quantity' có trong request.form không
    quantity = request.form.get('quantity')
    if quantity is None:
        flash('Số lượng không được phép trống!')
        return redirect(url_for('products'))

    # Chuyển đổi quantity sang kiểu số nguyên
    quantity = int(quantity)
    conn = get_db_connection()
    conn.execute('INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)',
                 (session['user_id'], product_id, quantity))
    conn.commit()
    flash('Sản phẩm đã được thêm vào giỏ hàng!')
    conn.close()
    return redirect(url_for('products'))





# Xem giỏ hàng
@app.route('/cart')
def cart():
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập để xem giỏ hàng.')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cart_items = conn.execute('''SELECT p.*, c.quantity FROM cart c
                                  JOIN products p ON c.product_id = p.id
                                  WHERE c.user_id = ?''', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('cart.html', cart_items=cart_items)

@app.route('/remove_from_cart/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập để xóa sản phẩm khỏi giỏ hàng.')
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute('DELETE FROM cart WHERE user_id = ? AND product_id = ?',
                 (session['user_id'], product_id))
    conn.commit()
    flash('Sản phẩm đã được xóa khỏi giỏ hàng!')
    return redirect(url_for('cart'))


# Xem hóa đơn
@app.route('/invoices')
def invoices():
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập để xem hóa đơn.')
        return redirect(url_for('login'))

    conn = get_db_connection()
    invoices = conn.execute('SELECT * FROM invoices WHERE user_id = ?', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('invoices.html', invoices=invoices)

# Thêm hóa đơn
@app.route('/invoices/add', methods=['GET', 'POST'])
def add_invoice():
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập để thêm hóa đơn.')
        return redirect(url_for('login'))

    if request.method == 'POST':
        customer_name = request.form['customer_name']
        total_price = request.form['total_price']
        date = request.form['date']
        conn = get_db_connection()
        conn.execute('INSERT INTO invoices (customer_name, total_price, date, user_id) VALUES (?, ?, ?, ?)',
                     (customer_name, total_price, date, session['user_id']))
        conn.commit()
        flash('Hóa đơn đã được thêm thành công!')
        return redirect(url_for('invoices'))

    return render_template('add_invoice.html')

# Xóa hóa đơn
@app.route('/invoices/delete/<int:id>')
def delete_invoice(id):
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập để xóa hóa đơn.')
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute('DELETE FROM invoices WHERE id = ? AND user_id = ?', (id, session['user_id']))
    conn.commit()
    flash('Hóa đơn đã được xóa thành công!')
    return redirect(url_for('invoices'))

# Hàm lấy tất cả sản phẩm từ cơ sở dữ liệu
def get_all_products():
    if 'user_id' not in session:
        return []  # Hoặc bạn có thể ném một lỗi hoặc redirect đến trang đăng nhập
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM products WHERE user_id = ?', (session['user_id'],)).fetchall()
    conn.close()
    return products

@app.route('/store')
def store():
    products = get_all_products()  # Lấy danh sách sản phẩm từ cơ sở dữ liệu
    return render_template('store.html', products=products)

@app.route('/report')
def report():
    # Logic cho báo cáo
    return render_template('report.html')

@app.route('/upload_image/<int:id>', methods=['POST'])
def upload_image(id):
    product = Product.query.get(id)
    if request.method == 'POST':
        if 'image' not in request.files:
            flash('Không có tệp hình ảnh nào được chọn!', 'danger')
            return redirect(url_for('product_management'))

        file = request.files['image']
        if file.filename == '':
            flash('Không có tệp nào được chọn!', 'danger')
            return redirect(url_for('product_management'))

        if file and allowed_file(file.filename):
            filename = f"{product.id}.jpg"  # Đặt tên tệp theo ID sản phẩm
            file.save(os.path.join(app.static_folder, 'images', filename))  # Lưu vào thư mục images
            flash('Hình ảnh đã được cập nhật!', 'success')
        else:
            flash('Định dạng tệp không hợp lệ! Chỉ cho phép hình ảnh JPEG.', 'danger')
    
    return redirect(url_for('product_management'))
    







if __name__ == '__main__':
    initialize_db()
    app.run(host='0.0.0.0', port=5000, debug=True)