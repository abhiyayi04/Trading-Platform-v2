from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user,
    logout_user, login_required, current_user
)
from flask_bcrypt import Bcrypt
from apscheduler.schedulers.background import BackgroundScheduler
from functools import wraps
from datetime import datetime
import atexit, os, random

app = Flask(__name__)

# silence missing icon requests
@app.route('/favicon.ico')
@app.route('/apple-touch-icon.png')
@app.route('/apple-touch-icon-precomposed.png')
def no_icon():
    return ('', 204)

# ---------------- Configuration ---------------- #
app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://root:password@localhost/stock_trading_db2"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# ---------------- Flask-Login setup ---------------- #
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# ---------------- MODELS ---------------- #
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(250), nullable=False)
    name = db.Column(db.String(100), nullable=False, unique=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    role = db.Column(db.String(50), default="customer", nullable=False)
    funds = db.Column(db.Float, default=10000.0)

    portfolio = db.relationship("Portfolio", backref="user", lazy=True)

class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)
    symbol = db.Column(db.String(10), nullable=False, unique=True)
    price = db.Column(db.Float, nullable=False)
    volume = db.Column(db.Float, nullable=False)

class Portfolio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    stock_id = db.Column(db.Integer, db.ForeignKey("stock.id"), nullable=False)
    quantity = db.Column(db.Float, default=0.0)
    stock = db.relationship("Stock")

class FinancialTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    type = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    balance_after = db.Column(db.Float, nullable=False)
    note = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    user = db.relationship("User", backref=db.backref("transactions", lazy=True))

class PaymentMethod(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    brand = db.Column(db.String(20), nullable=False)
    last4 = db.Column(db.String(4), nullable=False)
    exp_month = db.Column(db.Integer, nullable=False)
    exp_year = db.Column(db.Integer, nullable=False)
    is_default = db.Column(db.Boolean, default=True)
    token = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    user = db.relationship("User", backref=db.backref("payment_methods", lazy=True))

# ---- Orders for PENDING / EXECUTED / CANCELED ----
class OrderStatus:
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    CANCELED = "CANCELED"

class OrderSide:
    BUY = "BUY"
    SELL = "SELL"

class TradeOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    stock_id = db.Column(db.Integer, db.ForeignKey("stock.id"), nullable=False, index=True)
    side = db.Column(db.String(4), nullable=False) 
    quantity = db.Column(db.Float, nullable=False)
    price_locked = db.Column(db.Float, nullable=False) 
    status = db.Column(db.String(10), default=OrderStatus.PENDING) 
    created_at = db.Column(db.DateTime, default=db.func.now(), index=True)
    executed_at = db.Column(db.DateTime)
    canceled_at = db.Column(db.DateTime)

    user = db.relationship("User", backref=db.backref("orders", lazy=True))
    stock = db.relationship("Stock")

# ---------------- Helpers ---------------- #
def record_txn(user_id: int, txn_type: str, amount: float, balance_after: float, note: str = None):
    t = FinancialTransaction(
        user_id=user_id,
        type=txn_type,
        amount=round(float(amount), 2),
        balance_after=round(float(balance_after), 2),
        note=note
    )
    db.session.add(t)

def customer_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "customer":
            abort(403)
        return view_func(*args, **kwargs)
    return wrapped

def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "admin":
            abort(403)
        return view_func(*args, **kwargs)
    return wrapped

# --- order helpers ---
def place_order(user: User, stock: Stock, side: str, qty: float) -> TradeOrder:
    if qty <= 0:
        raise ValueError("Quantity must be positive")
    order = TradeOrder(
        user_id=user.id,
        stock_id=stock.id,
        side=side,
        quantity=qty,
        price_locked=float(stock.price), 
        status=OrderStatus.PENDING
    )
    db.session.add(order)
    db.session.commit()
    return order

def _add_or_update_position(user_id: int, stock: Stock, qty_delta: float):
    holding = Portfolio.query.filter_by(user_id=user_id, stock_id=stock.id).first()
    if holding:
        holding.quantity = round(holding.quantity + qty_delta, 6)
        if holding.quantity <= 0:
            db.session.delete(holding)
    else:
        if qty_delta > 0:
            db.session.add(Portfolio(user_id=user_id, stock_id=stock.id, quantity=qty_delta))

def execute_order(order_id: int):
    order = TradeOrder.query.get_or_404(order_id)
    if order.status != OrderStatus.PENDING:
        return False, "Order is not pending."

    user = order.user
    stock = order.stock
    qty = float(order.quantity)
    total = round(order.price_locked * qty, 2)

    if order.side == OrderSide.BUY:
        if stock.volume < qty:
            return False, "Insufficient market volume."
        if user.funds < total:
            return False, "Insufficient funds."

        user.funds = round(user.funds - total, 2)
        stock.volume = round(stock.volume - qty, 6)
        _add_or_update_position(user.id, stock, +qty)
        record_txn(user.id, "BUY", total, user.funds,
                   note=f"BUY {qty} {stock.symbol} @ ${order.price_locked:.2f}")
    else: 
        holding = Portfolio.query.filter_by(user_id=user.id, stock_id=stock.id).first()
        if not holding or holding.quantity < qty:
            return False, "Not enough shares to sell."

        holding.quantity = round(holding.quantity - qty, 6)
        stock.volume = round(stock.volume + qty, 6)
        user.funds = round(user.funds + total, 2)
        if holding.quantity <= 0:
            db.session.delete(holding)
        record_txn(user.id, "SELL", total, user.funds,
                   note=f"SELL {qty} {stock.symbol} @ ${order.price_locked:.2f}")

    order.status = OrderStatus.EXECUTED
    order.executed_at = datetime.utcnow()
    db.session.commit()
    return True, "Order executed."

def cancel_order(order_id: int):
    order = TradeOrder.query.get_or_404(order_id)
    if order.status != OrderStatus.PENDING:
        return False, "Only pending orders can be canceled."
    order.status = OrderStatus.CANCELED
    order.canceled_at = datetime.utcnow()
    db.session.commit()
    return True, "Order canceled."

# ---------------- Create tables ---------------- #
with app.app_context():
    db.create_all()

# ---------------- Flask-Login user loader ---------------- #
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------- RANDOM PRICE GENERATOR ---------------- #
def update_price(current_price: float, drift: float = 0.0005) -> float:
    random_change = random.uniform(-0.01, 0.01) + drift
    new_price = current_price * (1 + random_change)
    return round(max(new_price, 0.01), 2)

def update_all_stock_prices():
    with app.app_context():
        for stock in Stock.query.all():
            stock.price = update_price(stock.price)
        db.session.commit()
        print("Stock prices updated")

# scheduler
scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(func=update_all_stock_prices, trigger="interval", seconds=30)
if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    scheduler.start()
atexit.register(lambda: scheduler.shutdown(wait=False))

# ---------------- AUTH ROUTES ---------------- #
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        hashed_password = bcrypt.generate_password_hash(request.form["password"]).decode("utf-8")
        new_user = User(
            full_name=request.form["full_name"],
            name=request.form["username"],
            email=request.form["email"],
            password=hashed_password,
            role="customer"
        )
        db.session.add(new_user)
        db.session.commit()
        flash("Account created! Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("sign_up.html")

@app.route("/admin-register", methods=["GET", "POST"])
def admin_register():
    if request.method == "POST":
        admin_key = request.form["admin_key"]
        if admin_key != "MY_SECRET_ADMIN_KEY":
            flash("Invalid admin key!", "danger")
            return redirect(url_for("admin_register"))

        hashed_password = bcrypt.generate_password_hash(request.form["password"]).decode("utf-8")
        new_admin = User(
            full_name=request.form["full_name"],
            name=request.form["username"],
            email=request.form["email"],
            password=hashed_password,
            role="admin"
        )
        db.session.add(new_admin)
        db.session.commit()
        flash("Admin account created! Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("admin_sign_up.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(email=request.form["email"]).first()
        if user and bcrypt.check_password_hash(user.password, request.form["password"]):
            login_user(user)
            flash("Logged in successfully!", "success")
            return redirect(url_for("home"))
        flash("Invalid credentials", "danger")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

# ---------------- ROLE-BASED LANDING ---------------- #
@app.route("/")
@login_required
def home():
    return redirect(url_for("admin_dashboard" if current_user.role == "admin" else "portfolio"))

# ---------------- CUSTOMER ROUTES ---------------- #
@app.route("/market")
@customer_required
def market():
    stocks = Stock.query.all()
    return render_template("market.html", stocks=stocks)

@app.route("/portfolio")
@customer_required
def portfolio():
    return render_template("portfolio.html", user=current_user)

# ------------ ORDER ROUTES ------------
@app.route("/order/buy/<int:stock_id>", methods=["POST"])
@customer_required
def order_buy(stock_id):
    stock = Stock.query.get_or_404(stock_id)
    qty = float(request.form["quantity"])
    try:
        order = place_order(current_user, stock, OrderSide.BUY, qty)
        flash(f"Buy order placed: {qty} {stock.symbol} @ ${order.price_locked:.2f} (PENDING)", "info")
    except Exception as e:
        flash(str(e), "danger")
    return redirect(url_for("market"))

@app.route("/order/sell/<int:portfolio_id>", methods=["POST"])
@customer_required
def order_sell(portfolio_id):
    holding = Portfolio.query.get_or_404(portfolio_id)
    qty = float(request.form["quantity"])
    stock = holding.stock
    try:
        order = place_order(current_user, stock, OrderSide.SELL, qty)
        flash(f"Sell order placed: {qty} {stock.symbol} @ ${order.price_locked:.2f} (PENDING)", "info")
    except Exception as e:
        flash(str(e), "danger")
    return redirect(url_for("portfolio"))

@app.route("/order/execute/<int:order_id>", methods=["POST"])
@customer_required
def order_execute(order_id):
    order = TradeOrder.query.get_or_404(order_id)
    if order.user_id != current_user.id and current_user.role != "admin":
        abort(403)
    ok, msg = execute_order(order_id)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for("transactions"))

@app.route("/order/cancel/<int:order_id>", methods=["POST"])
@customer_required
def order_cancel(order_id):
    order = TradeOrder.query.get_or_404(order_id)
    if order.user_id != current_user.id and current_user.role != "admin":
        abort(403)
    ok, msg = cancel_order(order_id)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for("transactions"))

# -------- Transactions -------- #
@app.route("/transactions", endpoint="transactions")
@customer_required
def transactions():
    orders = (TradeOrder.query
              .filter_by(user_id=current_user.id)
              .order_by(TradeOrder.created_at.desc()).all())
    txns = (FinancialTransaction.query
            .filter_by(user_id=current_user.id)
            .order_by(FinancialTransaction.created_at.desc()).all())
    return render_template("transactions.html", orders=orders, txns=txns)

# -------- Funds pages & actions-------- #
@app.route("/funds", methods=["GET"])
@customer_required
def funds():
    recent_txns = FinancialTransaction.query.filter_by(user_id=current_user.id)\
        .order_by(FinancialTransaction.created_at.desc()).limit(10).all()
    methods = PaymentMethod.query.filter_by(user_id=current_user.id)\
        .order_by(PaymentMethod.is_default.desc(), PaymentMethod.created_at.desc()).all()
    return render_template("funds.html", user=current_user, recent_txns=recent_txns, methods=methods)

@app.route("/funds/deposit", methods=["POST"])
@customer_required
def deposit_funds():
    try:
        amount = float(request.form.get("amount", "0").strip())
    except Exception:
        flash("Invalid amount.", "danger")
        return redirect(url_for("funds"))

    if amount <= 0:
        flash("Deposit must be greater than 0.", "warning")
        return redirect(url_for("funds"))

    pm_id = request.form.get("payment_method_id")
    if pm_id:
        pm = PaymentMethod.query.filter_by(id=pm_id, user_id=current_user.id).first()
    else:
        pm = PaymentMethod.query.filter_by(user_id=current_user.id, is_default=True).first()

    if not pm:
        flash("Please add a payment method before depositing.", "warning")
        return redirect(url_for("add_payment_method"))

    current_user.funds = round(current_user.funds + amount, 2)
    record_txn(current_user.id, "DEPOSIT", amount, current_user.funds,
               note=f"Deposit via {pm.brand} ••••{pm.last4}")
    db.session.commit()

    flash(f"Deposited ${amount:,.2f}", "success")
    return redirect(url_for("funds"))

@app.route("/funds/withdraw", methods=["POST"])
@customer_required
def withdraw_funds():
    try:
        amount = float(request.form.get("amount", "0").strip())
    except Exception:
        flash("Invalid amount.", "danger")
        return redirect(url_for("funds"))

    if amount <= 0:
        flash("Withdrawal must be greater than 0.", "warning")
        return redirect(url_for("funds"))

    if amount > current_user.funds:
        flash("Insufficient funds.", "danger")
        return redirect(url_for("funds"))

    current_user.funds = round(current_user.funds - amount, 2)
    record_txn(current_user.id, "WITHDRAW", amount, current_user.funds, note="User withdrawal")
    db.session.commit()

    flash(f"Withdrew ${amount:,.2f}", "success")
    return redirect(url_for("funds"))

# -------- Funds actions-------- #
@app.route("/api/funds/deposit", methods=["POST"])
@customer_required
def api_deposit_funds():
    if not request.is_json:
        return jsonify(ok=False, message="Invalid request"), 400
    try:
        amount = float(request.json.get("amount", 0))
    except Exception:
        return jsonify(ok=False, message="Invalid amount"), 400
    if amount <= 0:
        return jsonify(ok=False, message="Deposit must be greater than 0"), 400

    pm_id = request.json.get("payment_method_id")
    if pm_id:
        pm = PaymentMethod.query.filter_by(id=pm_id, user_id=current_user.id).first()
    else:
        pm = PaymentMethod.query.filter_by(user_id=current_user.id, is_default=True).first()
    if not pm:
        return jsonify(ok=False, message="No payment method on file"), 400

    current_user.funds = round(current_user.funds + amount, 2)
    record_txn(current_user.id, "DEPOSIT", amount, current_user.funds,
               note=f"Deposit via {pm.brand} ••••{pm.last4}")
    db.session.commit()
    return jsonify(ok=True, balance=current_user.funds, message=f"Deposited ${amount:,.2f}")

@app.route("/api/funds/withdraw", methods=["POST"])
@customer_required
def api_withdraw_funds():
    if not request.is_json:
        return jsonify(ok=False, message="Invalid request"), 400
    try:
        amount = float(request.json.get("amount", 0))
    except Exception:
        return jsonify(ok=False, message="Invalid amount"), 400
    if amount <= 0:
        return jsonify(ok=False, message="Withdrawal must be greater than 0"), 400
    if amount > current_user.funds:
        return jsonify(ok=False, message="Insufficient funds"), 400

    current_user.funds = round(current_user.funds - amount, 2)
    record_txn(current_user.id, "WITHDRAW", amount, current_user.funds, note="User withdrawal")
    db.session.commit()
    return jsonify(ok=True, balance=current_user.funds, message=f"Withdrew ${amount:,.2f}")

# ===== Payment method management ===== #
@app.route("/payment-methods", endpoint="payment_methods")
@customer_required
def payment_methods():
    return redirect(url_for("add_payment_method"))

@app.route("/payment-methods/add", methods=["GET", "POST"])
@customer_required
def add_payment_method():
    if request.method == "POST":
        brand = (request.form.get("brand") or "").strip().title()
        last4 = (request.form.get("last4") or "").strip()
        exp_month = request.form.get("exp_month")
        exp_year = request.form.get("exp_year")
        token = (request.form.get("token") or "").strip() 

        try:
            exp_month = int(exp_month)
            exp_year = int(exp_year)
        except Exception:
            flash("Invalid expiry.", "danger")
            return redirect(url_for("add_payment_method"))

        if brand not in {"Visa", "Mastercard", "Amex", "Discover"}:
            flash("Choose a valid brand.", "danger")
            return redirect(url_for("add_payment_method"))

        if not (last4.isdigit() and len(last4) == 4):
            flash("Enter last 4 digits only.", "danger")
            return redirect(url_for("add_payment_method"))

        count = PaymentMethod.query.filter_by(user_id=current_user.id).count()
        make_default = bool(request.form.get("is_default")) or count == 0
        if make_default:
            PaymentMethod.query.filter_by(user_id=current_user.id, is_default=True).update({"is_default": False})

        pm = PaymentMethod(
            user_id=current_user.id,
            brand=brand,
            last4=last4,
            exp_month=exp_month,
            exp_year=exp_year,
            token=token or None,
            is_default=make_default
        )
        db.session.add(pm)
        db.session.commit()
        flash("Payment method added.", "success")
        return redirect(url_for("funds"))

    return render_template("payment_methods_add.html")

@app.route("/payment-methods/default/<int:pm_id>", methods=["POST"])
@customer_required
def set_default_payment_method(pm_id):
    pm = PaymentMethod.query.filter_by(id=pm_id, user_id=current_user.id).first_or_404()
    PaymentMethod.query.filter_by(user_id=current_user.id, is_default=True).update({"is_default": False})
    pm.is_default = True
    db.session.commit()
    flash("Default payment method updated.", "success")
    return redirect(url_for("funds"))

@app.route("/payment-methods/delete/<int:pm_id>", methods=["POST"])
@customer_required
def delete_payment_method(pm_id):
    pm = PaymentMethod.query.filter_by(id=pm_id, user_id=current_user.id).first_or_404()
    was_default = pm.is_default
    db.session.delete(pm)
    db.session.commit()
    if was_default:
        new_default = PaymentMethod.query.filter_by(user_id=current_user.id).first()
        if new_default:
            new_default.is_default = True
            db.session.commit()
    flash("Payment method removed.", "info")
    return redirect(url_for("funds"))

@app.route("/profile", endpoint="profile")
@login_required
def profile():
    if current_user.role == "customer":
        return render_template("profile.html", user=current_user)
    if current_user.role == "admin":
        return render_template("admin_profile.html", user=current_user)
    flash("Unauthorized access.", "danger")
    return redirect(url_for("home"))

# ---------------- ADMIN ROUTES ---------------- #
@app.route("/admin")
@admin_required
def admin_dashboard():
    stocks = Stock.query.all()
    return render_template("admin_dashboard.html", stocks=stocks)

@app.route("/admin/update-stocks", methods=["POST"])
@admin_required
def update_stocks():
    for stock in Stock.query_all():
        pass 

    for stock in Stock.query.all():
        fields = {
            "company_name": request.form.get(f"company_name_{stock.id}"),
            "symbol": request.form.get(f"symbol_{stock.id}"),
            "price": request.form.get(f"price_{stock.id}"),
            "volume": request.form.get(f"volume_{stock.id}")
        }
        if fields["company_name"]: stock.company_name = fields["company_name"]
        if fields["symbol"]:       stock.symbol = fields["symbol"].upper().strip()
        if fields["price"] is not None and fields["price"] != "":  stock.price = float(fields["price"])
        if fields["volume"] is not None and fields["volume"] != "": stock.volume = float(fields["volume"])

    db.session.commit()
    flash("Stocks updated successfully!", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/create-stock", methods=["GET", "POST"])
@admin_required
def create_stock():
    if request.method == "POST":
        company_name = request.form["company_name"]
        symbol = request.form["symbol"].upper().strip()
        price = float(request.form["price"])
        volume = float(request.form["volume"])

        if Stock.query.filter_by(symbol=symbol).first():
            flash("Stock symbol already exists!", "danger")
            return redirect(url_for("create_stock"))

        db.session.add(Stock(company_name=company_name, symbol=symbol, price=price, volume=volume))
        db.session.commit()
        flash("Stock created successfully!", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("create_stock.html")

@app.route("/admin/delete-stock/<int:stock_id>", methods=["POST"])
@admin_required
def delete_stock(stock_id):
    stock = Stock.query.get_or_404(stock_id)
    db.session.delete(stock)
    db.session.commit()
    flash("Stock deleted successfully!", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/change-market", methods=["GET", "POST"])
@admin_required
def change_market():
    return render_template("change_market.html")

if __name__ == "__main__":
    app.run(debug=True)
