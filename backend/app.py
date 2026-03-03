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
from datetime import time
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS
from flask_cors import CORS

app = Flask(__name__)
DISABLE_OLD_UI = True

CORS(app, supports_credentials=True, resources={r"/api/*": {"origins": "http://localhost:5173"}})

# ---------------- Configuration ---------------- #
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS
app.config['SECRET_KEY'] = 'your-secret-key'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# ---------------- Flask-Login setup ---------------- #
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.unauthorized_handler
def api_unauthorized():
    # If it's an API request, return JSON instead of redirecting to /login
    if request.path.startswith("/api/"):
        return jsonify({"error": "UNAUTHORIZED"}), 401
    return redirect(url_for("login"))

# ---------------- MODELS ---------------- #
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(250), nullable=False)
    name = db.Column(db.String(100), nullable=False, unique=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    role = db.Column(db.String(50), default="customer", nullable=False)
    funds = db.Column(db.Float, default=0.0)

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

class MarketSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    open_time = db.Column(db.Time, default=time(9, 30))
    close_time = db.Column(db.Time, default=time(16, 0))
    is_open = db.Column(db.Boolean, default=True)
    admin_override = db.Column(db.Boolean, default=False)
    closed_dates = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, onupdate=db.func.now())

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
def ui_disabled():
    return jsonify({"error": "UI_DISABLED_USE_REACT"}), 404

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

# --- order helpers --- #
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
    order.executed_at = datetime.now()
    db.session.commit()
    return True, "Order executed."

def cancel_order(order_id: int):
    order = TradeOrder.query.get_or_404(order_id)
    if order.status != OrderStatus.PENDING:
        return False, "Only pending orders can be canceled."
    order.status = OrderStatus.CANCELED
    order.canceled_at = datetime.now()
    db.session.commit()
    return True, "Order canceled."

def get_json():
    data = request.get_json(silent=True)
    if data is None:
        return {}
    return data

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

# ------------- MARKET SETTINGS ---------------- #
def market_is_open():
    settings = MarketSettings.query.first()
    if not settings:
        return False

    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    if settings.admin_override:
        return settings.is_open 

    if not settings.is_open:
        return False

    if now.weekday() >= 5:
        return False

    default_holidays = {
        "2025-01-01",
        "2025-01-20",
        "2025-02-17",
        "2025-04-18",
        "2025-05-26",
        "2025-06-19",
        "2025-07-04",
        "2025-09-01",
        "2025-11-27",
        "2025-12-25",
    }

    closed_dates = {d.strip() for d in settings.closed_dates.split(",") if d.strip()}

    if today_str in default_holidays or today_str in closed_dates:
        return False

    return settings.open_time <= now.time() <= settings.close_time

def market_status():
    settings = MarketSettings.query.first()
    if not settings:
        return {
            "has_settings": False,
            "is_open": False,
            "reason": "NO_SETTINGS_ROW"
        }

    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    # Admin override wins
    if settings.admin_override:
        return {
            "has_settings": True,
            "admin_override": True,
            "is_open": bool(settings.is_open),
            "reason": "ADMIN_OVERRIDE"
        }

    if not settings.is_open:
        return {"has_settings": True, "is_open": False, "reason": "MARKET_DISABLED"}

    if now.weekday() >= 5:
        return {"has_settings": True, "is_open": False, "reason": "WEEKEND"}

    closed_dates = {d.strip() for d in (settings.closed_dates or "").split(",") if d.strip()}
    if today_str in closed_dates:
        return {"has_settings": True, "is_open": False, "reason": "CLOSED_DATE"}

    if not (settings.open_time <= now.time() <= settings.close_time):
        return {
            "has_settings": True,
            "is_open": False,
            "reason": "OUTSIDE_HOURS",
            "open_time": settings.open_time.strftime("%H:%M"),
            "close_time": settings.close_time.strftime("%H:%M"),
            "now": now.strftime("%H:%M"),
        }

    return {
        "has_settings": True,
        "is_open": True,
        "reason": "OPEN",
        "open_time": settings.open_time.strftime("%H:%M"),
        "close_time": settings.close_time.strftime("%H:%M"),
        "now": now.strftime("%H:%M"),
    }

app.jinja_env.globals.update(market_is_open=market_is_open)

# scheduler
scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(func=update_all_stock_prices, trigger="interval", seconds=10)
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
    #if DISABLE_OLD_UI:
    #    return ui_disabled()
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
    #if DISABLE_OLD_UI:
    #    return ui_disabled()
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

# ---------------- ROLE-BASED LANDING ---------------- #
@app.route("/")
@login_required
def home():
    #if DISABLE_OLD_UI:
        #return ui_disabled()
    return redirect(url_for("admin_dashboard" if current_user.role == "admin" else "portfolio"))

# ---------------- CUSTOMER ROUTES ---------------- #
@app.route("/market")
@customer_required
def market():
    if DISABLE_OLD_UI:
        return ui_disabled()
    stocks = Stock.query.all()
    return render_template("market.html", stocks=stocks)

@app.route("/portfolio")
@customer_required
def portfolio():
    #if DISABLE_OLD_UI:
    #    return ui_disabled()
    return render_template("portfolio.html", user=current_user)

# ------------ ORDER ROUTES ------------
@app.route("/order/buy/<int:stock_id>", methods=["POST"])
@customer_required
def order_buy(stock_id):
    if DISABLE_OLD_UI:
        return ui_disabled()
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
    if DISABLE_OLD_UI:
        return ui_disabled()
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
    if DISABLE_OLD_UI:
        return ui_disabled()
    if not market_is_open():
        flash("Market is closed! Orders can only be executed during open hours.", "warning")
        return redirect(url_for("transactions"))
    
    order = TradeOrder.query.get_or_404(order_id)
    if order.user_id != current_user.id and current_user.role != "admin":
        abort(403)
    ok, msg = execute_order(order_id)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for("transactions"))

@app.route("/order/cancel/<int:order_id>", methods=["POST"])
@customer_required
def order_cancel(order_id):
    if DISABLE_OLD_UI:
        return ui_disabled()
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
    if DISABLE_OLD_UI:
        return ui_disabled()
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
    if DISABLE_OLD_UI:
        return ui_disabled()
    recent_txns = FinancialTransaction.query.filter_by(user_id=current_user.id)\
        .order_by(FinancialTransaction.created_at.desc()).limit(10).all()
    methods = PaymentMethod.query.filter_by(user_id=current_user.id)\
        .order_by(PaymentMethod.is_default.desc(), PaymentMethod.created_at.desc()).all()
    return render_template("funds.html", user=current_user, recent_txns=recent_txns, methods=methods)

@app.route("/funds/deposit", methods=["POST"])
@customer_required
def deposit_funds():
    if DISABLE_OLD_UI:
        return ui_disabled()
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
    if DISABLE_OLD_UI:
        return ui_disabled()
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

# ---- Payment method management ---- #
@app.route("/payment-methods", endpoint="payment_methods")
@customer_required
def payment_methods():
    if DISABLE_OLD_UI:
        return ui_disabled()
    return redirect(url_for("add_payment_method"))

@app.route("/payment-methods/add", methods=["GET", "POST"])
@customer_required
def add_payment_method():
    if DISABLE_OLD_UI:
        return ui_disabled()
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
    if DISABLE_OLD_UI:
        return ui_disabled()
    pm = PaymentMethod.query.filter_by(id=pm_id, user_id=current_user.id).first_or_404()
    PaymentMethod.query.filter_by(user_id=current_user.id, is_default=True).update({"is_default": False})
    pm.is_default = True
    db.session.commit()
    flash("Default payment method updated.", "success")
    return redirect(url_for("funds"))

@app.route("/payment-methods/delete/<int:pm_id>", methods=["POST"])
@customer_required
def delete_payment_method(pm_id):
    if DISABLE_OLD_UI:
        return ui_disabled()
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
    if DISABLE_OLD_UI:
        return ui_disabled()
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
    settings = MarketSettings.query.first()
    if not settings:
        settings = MarketSettings()
        db.session.add(settings)
        db.session.commit()

    if request.method == "POST":
        if "clear_override" in request.form:
            settings.admin_override = False
            db.session.commit()
            flash("Admin override disabled. Market is back to normal schedule.", "info")
            return redirect(url_for("change_market"))
        
        if "toggle_market" in request.form:
            settings.admin_override = True
            settings.is_open = not settings.is_open
            db.session.commit()
            flash(f"Market manually {'opened' if settings.is_open else 'closed'} by admin.", "info")
            return redirect(url_for("change_market"))

        elif "open_time" in request.form and "close_time" in request.form:
            try:
                open_time = datetime.strptime(request.form["open_time"], "%H:%M").time()
                close_time = datetime.strptime(request.form["close_time"], "%H:%M").time()
                settings.open_time = open_time
                settings.close_time = close_time
                db.session.commit()
                flash("Market hours updated successfully!", "success")
                return redirect(url_for("change_market"))
            except Exception:
                flash("Invalid time format. Please enter valid times.", "danger")
                return redirect(url_for("change_market"))

        elif "closed_dates" in request.form:
            closed_dates_str = request.form.get("closed_dates", "").strip()
            if closed_dates_str:
                try:
                    dates = []
                    for d in closed_dates_str.split(","):
                        d = d.strip()
                        if not d:
                            continue
                        parsed = datetime.strptime(d, "%Y-%m-%d")
                        dates.append(parsed.strftime("%Y-%m-%d"))
                    settings.closed_dates = ", ".join(dates)
                except ValueError:
                    flash("Invalid date format. Please select dates using the date picker.", "danger")
                    return redirect(url_for("change_market"))
            else:
                settings.closed_dates = ""

            today_str = datetime.now().strftime("%Y-%m-%d")
            closed_set = set(d.strip() for d in settings.closed_dates.split(",") if d.strip())

            if today_str not in closed_set and not settings.is_open:
                settings.is_open = True
                flash("Today was removed from closed dates — market automatically reopened.", "info")

            db.session.commit()
            flash("Closed dates updated successfully!", "success")
            return redirect(url_for("change_market"))

    return render_template("change_market.html", settings=settings)


@app.route("/api/stocks", methods=["GET"])
@login_required
def api_stocks():
    stocks = Stock.query.all()
    return jsonify([
        {
            "id": s.id,
            "company_name": s.company_name,
            "symbol": s.symbol,
            "price": s.price,
            "volume": s.volume
        } for s in stocks
    ]), 200

@app.route("/api/me", methods=["GET"])
def api_me():
    if not current_user.is_authenticated:
        return jsonify({"authenticated": False}), 200

    return jsonify({
        "authenticated": True,
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role,
        "funds": current_user.funds
    }), 200

@app.route("/api/auth/register", methods=["POST"])
def api_register():
    data = request.get_json(silent=True) or {}

    full_name = (data.get("full_name") or "").strip()
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not full_name or not username or not email or not password:
        return jsonify({"error": "MISSING_FIELDS"}), 400

    if len(password) < 6:
        return jsonify({"error": "WEAK_PASSWORD"}), 400

    # unique checks
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "EMAIL_EXISTS"}), 409

    if User.query.filter_by(name=username).first():
        return jsonify({"error": "USERNAME_EXISTS"}), 409

    hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

    new_user = User(
        full_name=full_name,
        name=username,
        email=email,
        password=hashed_password,
        role="customer",
        funds=0.0
    )

    db.session.add(new_user)
    db.session.commit()

    return jsonify({
        "message": "REGISTERED",
        "user": {
            "id": new_user.id,
            "name": new_user.name,
            "email": new_user.email,
            "role": new_user.role,
            "funds": new_user.funds
        }
    }), 201

@app.route("/api/auth/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "MISSING_FIELDS"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not bcrypt.check_password_hash(user.password, password):
        return jsonify({"error": "INVALID_CREDENTIALS"}), 401

    login_user(user)
    return jsonify({
        "message": "LOGGED_IN",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "funds": user.funds
        }
    }), 200

@app.route("/api/auth/logout", methods=["POST"])
@login_required
def api_logout():
    logout_user()
    return jsonify({"message": "LOGGED_OUT"}), 200

@app.route("/api/orders", methods=["POST"])
@customer_required
def api_place_order():
    data = get_json()
    side = (data.get("side") or "").upper().strip()
    stock_id = data.get("stock_id")
    quantity = data.get("quantity")

    if side not in {OrderSide.BUY, OrderSide.SELL}:
        return jsonify({"error": "INVALID_SIDE"}), 400

    try:
        stock_id = int(stock_id)
        quantity = float(quantity)
    except Exception:
        return jsonify({"error": "INVALID_INPUT"}), 400

    stock = Stock.query.get_or_404(stock_id)

    try:
        order = place_order(current_user, stock, side, quantity)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({
        "message": "ORDER_PLACED",
        "order": {
            "id": order.id,
            "stock_id": order.stock_id,
            "side": order.side,
            "quantity": order.quantity,
            "price_locked": order.price_locked,
            "status": order.status,
            "created_at": order.created_at.isoformat() if order.created_at else None
        }
    }), 201

@app.route("/api/orders/<int:order_id>/execute", methods=["POST"])
@customer_required
def api_execute_order(order_id):
    if not market_is_open():
        return jsonify({"error": "MARKET_CLOSED"}), 400

    order = TradeOrder.query.get_or_404(order_id)

    # Only owner can execute (admin support later)
    if order.user_id != current_user.id:
        return jsonify({"error": "FORBIDDEN"}), 403

    ok, msg = execute_order(order_id)
    if not ok:
        return jsonify({"error": msg}), 400

    return jsonify({"message": msg}), 200

@app.route("/api/orders/<int:order_id>/cancel", methods=["POST"])
@customer_required
def api_cancel_order(order_id):
    order = TradeOrder.query.get_or_404(order_id)

    if order.user_id != current_user.id:
        return jsonify({"error": "FORBIDDEN"}), 403

    ok, msg = cancel_order(order_id)
    if not ok:
        return jsonify({"error": msg}), 400

    return jsonify({"message": msg}), 200

@app.route("/api/orders", methods=["GET"])
@customer_required
def api_get_orders():
    orders = (TradeOrder.query
              .filter_by(user_id=current_user.id)
              .order_by(TradeOrder.created_at.desc())
              .all())

    return jsonify([
        {
            "id": o.id,
            "stock_id": o.stock_id,
            "side": o.side,
            "quantity": o.quantity,
            "price_locked": o.price_locked,
            "status": o.status,
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "executed_at": o.executed_at.isoformat() if o.executed_at else None,
            "canceled_at": o.canceled_at.isoformat() if o.canceled_at else None,
            "symbol": o.stock.symbol,
            "company_name": o.stock.company_name
        } for o in orders
    ]), 200

@app.route("/api/portfolio", methods=["GET"])
@customer_required
def api_portfolio():
    # current user cash
    cash = round(float(current_user.funds or 0), 2)

    # holdings from Portfolio table
    holdings = Portfolio.query.filter_by(user_id=current_user.id).all()

    # Build avg_cost using EXECUTED BUY orders
    executed_buys = (
        TradeOrder.query
        .filter_by(user_id=current_user.id, status=OrderStatus.EXECUTED, side=OrderSide.BUY)
        .all()
    )

    # avg_cost_map[stock_id] = (total_cost, total_qty)
    avg_cost_map = {}
    for o in executed_buys:
        cost = float(o.price_locked) * float(o.quantity)
        qty = float(o.quantity)

        if o.stock_id not in avg_cost_map:
            avg_cost_map[o.stock_id] = {"cost": 0.0, "qty": 0.0}

        avg_cost_map[o.stock_id]["cost"] += cost
        avg_cost_map[o.stock_id]["qty"] += qty

    result_holdings = []
    holdings_value = 0.0

    for h in holdings:
        stock = h.stock
        qty = float(h.quantity)
        current_price = float(stock.price)

        avg_cost = 0.0
        if stock.id in avg_cost_map and avg_cost_map[stock.id]["qty"] > 0:
            avg_cost = avg_cost_map[stock.id]["cost"] / avg_cost_map[stock.id]["qty"]

        market_value = qty * current_price
        holdings_value += market_value

        unrealized_pl = (current_price - avg_cost) * qty
        unrealized_pl_pct = 0.0
        if avg_cost > 0:
            unrealized_pl_pct = ((current_price - avg_cost) / avg_cost) * 100

        result_holdings.append({
            "stock_id": stock.id,
            "company_name": stock.company_name,
            "symbol": stock.symbol,
            "quantity": round(qty, 6),
            "avg_cost": round(avg_cost, 2),
            "current_price": round(current_price, 2),
            "market_value": round(market_value, 2),
            "unrealized_pl": round(unrealized_pl, 2),
            "unrealized_pl_pct": round(unrealized_pl_pct, 2),
        })

    holdings_value = round(holdings_value, 2)
    total_equity = round(cash + holdings_value, 2)

    return jsonify({
        "cash": cash,
        "holdings_value": holdings_value,
        "total_equity": total_equity,
        "holdings": result_holdings
    }), 200

# ---------------- FUNDS API ---------------- #

@app.route("/api/funds", methods=["GET"])
@customer_required
def api_funds():
    recent_txns = (FinancialTransaction.query
                   .filter_by(user_id=current_user.id)
                   .order_by(FinancialTransaction.created_at.desc())
                   .limit(10).all())

    methods = (PaymentMethod.query
               .filter_by(user_id=current_user.id)
               .order_by(PaymentMethod.is_default.desc(), PaymentMethod.created_at.desc())
               .all())

    return jsonify({
        "cash": round(float(current_user.funds or 0), 2),
        "recent_txns": [
            {
                "id": t.id,
                "type": t.type,
                "amount": float(t.amount),
                "balance_after": float(t.balance_after),
                "note": t.note,
                "created_at": t.created_at.isoformat() if t.created_at else None
            } for t in recent_txns
        ],
        "payment_methods": [
            {
                "id": pm.id,
                "brand": pm.brand,
                "last4": pm.last4,
                "exp_month": pm.exp_month,
                "exp_year": pm.exp_year,
                "is_default": bool(pm.is_default)
            } for pm in methods
        ]
    }), 200


@app.route("/api/funds/deposit", methods=["POST"])
@customer_required
def api_deposit_funds():
    data = get_json()
    amount = data.get("amount")
    payment_method_id = data.get("payment_method_id")

    try:
        amount = float(amount)
    except Exception:
        return jsonify({"error": "INVALID_AMOUNT"}), 400

    if amount <= 0:
        return jsonify({"error": "AMOUNT_MUST_BE_POSITIVE"}), 400

    if payment_method_id:
        try:
            payment_method_id = int(payment_method_id)
        except Exception:
            return jsonify({"error": "INVALID_PAYMENT_METHOD"}), 400

        pm = PaymentMethod.query.filter_by(
            id=payment_method_id,
            user_id=current_user.id
        ).first()
    else:
        pm = PaymentMethod.query.filter_by(
            user_id=current_user.id,
            is_default=True
        ).first()

    if not pm:
        return jsonify({"error": "NO_PAYMENT_METHOD"}), 400

    current_user.funds = round(float(current_user.funds or 0) + amount, 2)
    record_txn(current_user.id, "DEPOSIT", amount, current_user.funds,
               note=f"Deposit via {pm.brand} ••••{pm.last4}")

    db.session.commit()

    return jsonify({
        "message": "DEPOSIT_OK",
        "cash": float(current_user.funds)
    }), 200


@app.route("/api/funds/withdraw", methods=["POST"])
@customer_required
def api_withdraw_funds():
    data = get_json()
    amount = data.get("amount")

    try:
        amount = float(amount)
    except Exception:
        return jsonify({"error": "INVALID_AMOUNT"}), 400

    if amount <= 0:
        return jsonify({"error": "AMOUNT_MUST_BE_POSITIVE"}), 400

    cash = float(current_user.funds or 0)
    if amount > cash:
        return jsonify({"error": "INSUFFICIENT_FUNDS"}), 400

    current_user.funds = round(cash - amount, 2)
    record_txn(current_user.id, "WITHDRAW", amount, current_user.funds, note="User withdrawal")

    db.session.commit()

    return jsonify({
        "message": "WITHDRAW_OK",
        "cash": float(current_user.funds)
    }), 200

@app.route("/api/market/status", methods=["GET"])
def api_market_status():
    return jsonify(market_status()), 200

if __name__ == "__main__":
    app.run(debug=True)
