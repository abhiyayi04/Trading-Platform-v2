from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user,
    logout_user, login_required, current_user
)
from flask_bcrypt import Bcrypt
from apscheduler.schedulers.background import BackgroundScheduler
import atexit, os, random

app = Flask(__name__)

# ---------------- Configuration ---------------- #
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:password@localhost/stock_trading_db2'
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

# ---------------- Create tables ---------------- #
with app.app_context():
    db.create_all()

# ---------------- Flask-Login user loader ---------------- #
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------- RANDOM PRICE GENERATOR ---------------- #
def update_price(current_price: float, drift: float = 0.0005) -> float:
    """Simulates small random price fluctuations with a gentle upward drift."""
    random_change = random.uniform(-0.01, 0.01) + drift
    new_price = current_price * (1 + random_change)
    return round(max(new_price, 0.01), 2)

def update_all_stock_prices():
    """Automatically updates all stock prices every 30s."""
    with app.app_context():
        for stock in Stock.query.all():
            stock.price = update_price(stock.price)
        db.session.commit()
        print("✅ Stock prices updated")

# Start scheduler only in the main reloader process
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
@login_required
def market():
    if current_user.role != "customer":
        flash("Unauthorized access.", "danger")
        return redirect(url_for("home"))
    stocks = Stock.query.all()
    return render_template("market.html", stocks=stocks)

@app.route("/portfolio")
@login_required
def portfolio():
    if current_user.role != "customer":
        flash("Unauthorized access.", "danger")
        return redirect(url_for("home"))
    return render_template("portfolio.html", user=current_user)

# BUY STOCK
@app.route("/buy/<int:stock_id>", methods=["POST"])
@login_required
def buy_stock(stock_id):
    if current_user.role != "customer":
        flash("Unauthorized action.", "danger")
        return redirect(url_for("home"))

    stock = Stock.query.get_or_404(stock_id)
    qty = float(request.form["quantity"])
    total_cost = stock.price * qty

    if stock.volume < qty:
        flash("Not enough stock volume available!", "danger")
        return redirect(url_for("market"))

    if current_user.funds >= total_cost:
        current_user.funds -= total_cost
        stock.volume -= qty
        holding = Portfolio.query.filter_by(user_id=current_user.id, stock_id=stock.id).first()
        if holding:
            holding.quantity += qty
        else:
            db.session.add(Portfolio(user_id=current_user.id, stock_id=stock.id, quantity=qty))
        db.session.commit()
        flash("Stock bought successfully!", "success")
    else:
        flash("Not enough funds to buy this stock!", "danger")

    return redirect(url_for("market"))

# SELL STOCK
@app.route("/sell/<int:portfolio_id>", methods=["POST"])
@login_required
def sell_stock(portfolio_id):
    if current_user.role != "customer":
        flash("Unauthorized action.", "danger")
        return redirect(url_for("home"))

    holding = Portfolio.query.get_or_404(portfolio_id)
    qty = float(request.form["quantity"])

    if holding.quantity < qty:
        flash("Not enough shares to sell!", "danger")
        return redirect(url_for("portfolio"))

    holding.quantity -= qty
    holding.stock.volume += qty
    current_user.funds += holding.stock.price * qty

    if holding.quantity <= 0:
        db.session.delete(holding)

    db.session.commit()
    flash("Stock sold successfully!", "success")
    return redirect(url_for("portfolio"))

@app.route("/funds", methods=["GET"])
@login_required
def funds():
    if current_user.role != "customer":
        flash("Unauthorized access.", "danger")
        return redirect(url_for("home"))
    return render_template("funds.html")

@app.route("/transactions")
@login_required
def transactions():
    if current_user.role != "customer":
        flash("Unauthorized access.", "danger")
        return redirect(url_for("home"))
    return render_template("transactions.html")

@app.route("/profile")
@login_required
def profile():
    if current_user.role == "customer":
        return render_template("profile.html", user=current_user)
    if current_user.role == "admin":
        return render_template("admin_profile.html", user=current_user)
    flash("Unauthorized access.", "danger")
    return redirect(url_for("home"))

@app.route("/settings")
@login_required
def settings():
    if current_user.role != "customer":
        flash("Unauthorized access.", "danger")
        return redirect(url_for("home"))
    return render_template("settings.html")

# ---------------- ADMIN ROUTES ---------------- #
@app.route("/admin")
@login_required
def admin_dashboard():
    if current_user.role != "admin":
        flash("Unauthorized access.", "danger")
        return redirect(url_for("home"))
    stocks = Stock.query.all()
    return render_template("admin_dashboard.html", stocks=stocks)

@app.route("/admin/update-stocks", methods=["POST"])
@login_required
def update_stocks():
    if current_user.role != "admin":
        flash("Unauthorized access.", "danger")
        return redirect(url_for("home"))

    for stock in Stock.query.all():
        fields = {
            "company_name": request.form.get(f"company_name_{stock.id}"),
            "symbol": request.form.get(f"symbol_{stock.id}"),
            "price": request.form.get(f"price_{stock.id}"),
            "volume": request.form.get(f"volume_{stock.id}")
        }
        if fields["company_name"]: stock.company_name = fields["company_name"]
        if fields["symbol"]:       stock.symbol = fields["symbol"].upper().strip()
        if fields["price"] is not None:  stock.price = float(fields["price"])
        if fields["volume"] is not None: stock.volume = float(fields["volume"])

    db.session.commit()
    flash("Stocks updated successfully!", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/create-stock", methods=["GET", "POST"])
@login_required
def create_stock():
    if current_user.role != "admin":
        flash("Unauthorized access.", "danger")
        return redirect(url_for("home"))

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
@login_required
def delete_stock(stock_id):
    if current_user.role != "admin":
        flash("Unauthorized access.", "danger")
        return redirect(url_for("home"))

    stock = Stock.query.get_or_404(stock_id)
    db.session.delete(stock)
    db.session.commit()
    flash("Stock deleted successfully!", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/change-market", methods=["GET", "POST"])
@login_required
def change_market():
    if current_user.role != "admin":
        flash("Unauthorized access.", "danger")
        return redirect(url_for("home"))
    return render_template("change_market.html")

if __name__ == "__main__":
    app.run(debug=True)
