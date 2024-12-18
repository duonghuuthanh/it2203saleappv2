import math

from flask import render_template, request, redirect, jsonify, session
import dao, utils
from app import app, login
from flask_login import login_user, logout_user
from app.models import UserRole


@app.route("/")
def index():
    cate_id = request.args.get('category_id')
    kw = request.args.get('kw')
    page = request.args.get('page', 1)

    prods = dao.load_products(cate_id=cate_id, kw=kw, page=int(page))

    total = dao.count_products()
    page_size = app.config['PAGE_SIZE']
    return render_template("index.html", products=prods, pages=math.ceil(total/page_size))


@app.route('/products/<product_id>')
def details(product_id):
    return render_template('details.html',
                           product=dao.get_product_by_id(product_id),
                           comments=dao.load_comments(product_id))


@app.route('/api/products/<product_id>/comments', methods=['post'])
def add_comment(product_id):
    c = dao.add_comment(content=request.json.get('content'), product_id=product_id)
    return {
        'content': c.content,
        'created_date': c.created_date,
        'user': {
            'avatar': c.user.avatar
        }
    }


@app.route("/login", methods=['get', 'post'])
def login_process():
    if request.method.__eq__("POST"):
        username = request.form.get('username')
        password = request.form.get('password')
        user = dao.auth_user(username=username, password=password)
        if user:
            login_user(user)

            next = request.args.get('next')
            return redirect(next if next else '/')

    return render_template('login.html')


@app.route('/login-admin', methods=['post'])
def login_admin_process():
    username = request.form.get('username')
    password = request.form.get('password')
    user = dao.auth_user(username=username, password=password, role=UserRole.ADMIN)
    if user:
        login_user(user)

    return redirect('/admin')


@app.route("/logout")
def logout_process():
    logout_user()
    return redirect('/login')


@app.route('/register', methods=['get', 'post'])
def register_process():
    err_msg = ''
    if request.method.__eq__('POST'):
        password = request.form.get('password')
        confirm = request.form.get('confirm')
        if password.__eq__(confirm):
            data = request.form.copy()
            del data['confirm']

            dao.add_user(avatar=request.files.get('avatar'), **data)

            return redirect('/login')
        else:
            err_msg = 'Mật khẩu không khớp!'

    return render_template('register.html', err_msg=err_msg)


@app.route('/api/carts', methods=['post'])
def add_to_cart():
    """
    {
        "1": {
            "id": "1",
            "name": "..",
            "price": 123,
            "quantity": 2
        }, "2": {
            "id": "2",
            "name": "..",
            "price": 123,
            "quantity": 1
        }
    }
    """
    cart = session.get('cart')
    if not cart:
        cart = {}

    id = str(request.json.get('id'))
    name = request.json.get('name')
    price = request.json.get('price')

    if id in cart:
        cart[id]["quantity"] += 1
    else:
        cart[id] = {
            "id": id,
            "name": name,
            "price": price,
            "quantity": 1
        }

    session['cart'] = cart
    print(cart)

    return jsonify(utils.stats_cart(cart))


@app.route('/api/carts/<product_id>', methods=['put'])
def update_cart(product_id):
    cart = session.get('cart')

    if cart and product_id in cart:
        quantity = int(request.json.get('quantity', 0))
        cart[product_id]['quantity'] = quantity

    session['cart'] = cart

    return jsonify(utils.stats_cart(cart))


@app.route('/api/carts/<product_id>', methods=['delete'])
def delete_cart(product_id):
    cart = session.get('cart')

    if cart and product_id in cart:
        del cart[product_id]

    session['cart'] = cart

    return jsonify(utils.stats_cart(cart))


@app.route('/api/pay', methods=['post'])
def pay():
    try:
        dao.add_receipt(session.get('cart'))
    except:
        return jsonify({'status': 500})
    else:
        del session['cart']
        return jsonify({'status': 200})


@app.route('/cart')
def cart():
    return render_template('cart.html')


@app.context_processor
def common_response():
    return {
        'categories': dao.load_categories(),
        'cart_stats': utils.stats_cart(session.get('cart'))
    }


@login.user_loader
def get_user_by_id(user_id):
    return dao.get_user_by_id(user_id)


if __name__ == '__main__':
    with app.app_context():
        from app import admin
        app.run(debug=True)
