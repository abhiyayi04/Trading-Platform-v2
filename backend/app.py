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
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()

CORS(app, supports_credentials=True, resources={r"/api/*": {"origins": "http://localhost:5173"}})

# ---------------- Configuration ---------------- #
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=not app.debug
)

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
    return db.session.get(User, int(user_id))

# ---------------- RANDOM PRICE GENERATOR ---------------- #
def update_price(current_price: float, drift: float = 0.0005) -> float:
    random_change = random.uniform(-0.01, 0.01) + drift
    new_price = current_price * (1 + random_change)
    return round(max(new_price, 0.01), 2)

def update_all_stock_prices():
    with app.app_context():
        if not market_is_open():
            return

        for stock in Stock.query.all():
            stock.price = update_price(float(stock.price))
        db.session.commit()

# ------------- MARKET SETTINGS ---------------- #
def default_holidays_set():
    return {
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

def get_closed_dates(settings: MarketSettings):
    # DB closed dates + built-in holidays
    db_dates = {d.strip() for d in (settings.closed_dates or "").split(",") if d.strip()}
    return default_holidays_set() | db_dates

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

    closed = get_closed_dates(settings)

    if today_str in closed:
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

    closed = get_closed_dates(settings)
    if today_str in closed:
        return {"has_settings": True, "is_open": False, "reason": "HOLIDAY_OR_CLOSED_DATE"}

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

def start_scheduler():
    if app.debug:
        if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
            return
    if not scheduler.running:
        scheduler.start()
        atexit.register(lambda: scheduler.shutdown(wait=False))

start_scheduler()

# ---------------- API ROUTES ---------------- #

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

    role = (data.get("role") or "customer").strip().lower()
    admin_key = (data.get("admin_key") or "").strip()

    if not full_name or not username or not email or not password:
        return jsonify({"error": "MISSING_FIELDS"}), 400

    if role not in {"customer", "admin"}:
        return jsonify({"error": "INVALID_ROLE"}), 400

    if role == "admin":
        expected = os.getenv("ADMIN_SECRET_KEY")
        if not expected or admin_key != expected:
            return jsonify({"error": "INVALID_ADMIN_SECRET"}), 403

    if len(password) < 6:
        return jsonify({"error": "WEAK_PASSWORD"}), 400

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
        role=role,
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

@app.route("/api/admin/market/toggle", methods=["POST"])
@admin_required
def api_admin_market_toggle():
    settings = MarketSettings.query.first()
    if not settings:
        settings = MarketSettings()
        db.session.add(settings)
        db.session.commit()

    # Enable admin override and flip open/close
    settings.admin_override = True
    settings.is_open = not settings.is_open
    db.session.commit()

    return jsonify({
        "message": "TOGGLED",
        "admin_override": settings.admin_override,
        "is_open": settings.is_open
    }), 200

@app.route("/api/admin/stocks", methods=["GET"])
@admin_required
def api_admin_stocks():
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

@app.route("/api/admin/stocks", methods=["POST"])
@admin_required
def api_admin_create_stock():
    data = request.get_json(silent=True) or {}

    company_name = (data.get("company_name") or "").strip()
    symbol = (data.get("symbol") or "").strip().upper()
    price = data.get("price")
    volume = data.get("volume")

    if not company_name or not symbol or price is None or volume is None:
        return jsonify({"error": "MISSING_FIELDS"}), 400

    try:
        price = float(price)
        volume = float(volume)
    except Exception:
        return jsonify({"error": "INVALID_NUMBER"}), 400

    if price <= 0 or volume < 0:
        return jsonify({"error": "INVALID_VALUES"}), 400

    if Stock.query.filter_by(symbol=symbol).first():
        return jsonify({"error": "SYMBOL_EXISTS"}), 409

    s = Stock(company_name=company_name, symbol=symbol, price=price, volume=volume)
    db.session.add(s)
    db.session.commit()

    return jsonify({
        "message": "CREATED",
        "stock": {
            "id": s.id,
            "company_name": s.company_name,
            "symbol": s.symbol,
            "price": s.price,
            "volume": s.volume
        }
    }), 201


@app.route("/api/admin/stocks/<int:stock_id>", methods=["DELETE"])
@admin_required
def api_admin_delete_stock(stock_id):
    s = Stock.query.get_or_404(stock_id)
    db.session.delete(s)
    db.session.commit()
    return jsonify({"message": "DELETED"}), 200

@app.route("/api/admin/market/hours", methods=["POST"])
@admin_required
def api_admin_market_set_hours():
    data = request.get_json(silent=True) or {}
    open_time = data.get("open_time")  # "HH:MM"
    close_time = data.get("close_time")  # "HH:MM"

    if not open_time or not close_time:
        return jsonify({"error": "MISSING_FIELDS"}), 400

    try:
        ot = datetime.strptime(open_time, "%H:%M").time()
        ct = datetime.strptime(close_time, "%H:%M").time()
    except Exception:
        return jsonify({"error": "INVALID_TIME"}), 400

    settings = MarketSettings.query.first()
    if not settings:
        settings = MarketSettings()
        db.session.add(settings)
        db.session.commit()

    settings.open_time = ot
    settings.close_time = ct
    db.session.commit()

    return jsonify({
        "message": "HOURS_UPDATED",
        "open_time": settings.open_time.strftime("%H:%M"),
        "close_time": settings.close_time.strftime("%H:%M"),
    }), 200

@app.route("/api/admin/market/closed-dates", methods=["POST"])
@admin_required
def api_admin_market_set_closed_dates():
    data = request.get_json(silent=True) or {}
    dates = data.get("dates")  # ["YYYY-MM-DD", ...]

    if not isinstance(dates, list):
        return jsonify({"error": "INVALID_DATES"}), 400

    normalized = []
    try:
        for d in dates:
            d = (d or "").strip()
            parsed = datetime.strptime(d, "%Y-%m-%d")
            normalized.append(parsed.strftime("%Y-%m-%d"))
    except Exception:
        return jsonify({"error": "INVALID_DATE_FORMAT"}), 400

    settings = MarketSettings.query.first()
    if not settings:
        settings = MarketSettings()
        db.session.add(settings)
        db.session.commit()

    settings.closed_dates = ", ".join(sorted(set(normalized)))
    db.session.commit()

    return jsonify({
        "message": "CLOSED_DATES_UPDATED",
        "closed_dates": settings.closed_dates
    }), 200

if __name__ == "__main__":
    app.run(debug=True)
