from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user,
    logout_user, login_required, current_user
)
from flask_bcrypt import Bcrypt

app = Flask(__name__)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Chikku04mysql@localhost/stock_trading_db2'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# MODELS
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
    symbol = db.Column(db.String(10), nullable=False, unique=True)
    price = db.Column(db.Float, nullable=False)


class Portfolio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    stock_id = db.Column(db.Integer, db.ForeignKey("stock.id"), nullable=False)
    quantity = db.Column(db.Integer, default=0)

    stock = db.relationship("Stock")


# Create tables
with app.app_context():
    db.create_all()


# Flask-Login user loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# AUTH ROUTES
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
        else:
            flash("Invalid credentials", "danger")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# ROLE-BASED LANDING
@app.route("/")
@login_required
def home():
    if current_user.role == "admin":
        return redirect(url_for("admin_dashboard"))
    else:
        return redirect(url_for("portfolio"))


# CUSTOMER ROUTES
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
    user = current_user
    return render_template("portfolio.html", user=user)


# BUY STOCK
@app.route("/buy/<int:stock_id>", methods=["POST"])
@login_required
def buy_stock(stock_id):
    if current_user.role != "customer":
        flash("Unauthorized action.", "danger")
        return redirect(url_for("home"))

    stock = Stock.query.get_or_404(stock_id)
    user = current_user
    qty = int(request.form["quantity"])
    total_cost = stock.price * qty

    if user.funds >= total_cost:
        user.funds -= total_cost
        portfolio = Portfolio.query.filter_by(user_id=user.id, stock_id=stock.id).first()
        if portfolio:
            portfolio.quantity += qty
        else:
            new_portfolio = Portfolio(user_id=user.id, stock_id=stock.id, quantity=qty)
            db.session.add(new_portfolio)

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

    portfolio_item = Portfolio.query.get_or_404(portfolio_id)
    user = current_user
    qty = int(request.form["quantity"])

    if portfolio_item.quantity >= qty:
        portfolio_item.quantity -= qty
        user.funds += portfolio_item.stock.price * qty

        if portfolio_item.quantity == 0:
            db.session.delete(portfolio_item)

        db.session.commit()
        flash("Stock sold successfully!", "success")
    else:
        flash("Not enough shares to sell!", "danger")

    return redirect(url_for("portfolio"))


@app.route("/funds")
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
    elif current_user.role == "admin":
        return render_template("admin_profile.html", user=current_user)
    else:
        flash("Unauthorized access.", "danger")
        return redirect(url_for("home"))


@app.route("/settings")
@login_required
def settings():
    if current_user.role != "customer":
        flash("Unauthorized access.", "danger")
        return redirect(url_for("home"))
    return render_template("settings.html")


# ADMIN ROUTES
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

    stocks = Stock.query.all()
    for stock in stocks:
        symbol_field = f"symbol_{stock.id}"
        price_field = f"price_{stock.id}"
        if symbol_field in request.form and price_field in request.form:
            stock.symbol = request.form[symbol_field]
            stock.price = float(request.form[price_field])
    db.session.commit()
    flash("Stocks updated successfully!", "success")
    return redirect(url_for("admin_dashboard"))


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

@app.route("/admin/create-stock", methods=["GET", "POST"])
@login_required
def create_stock():
    if current_user.role != "admin":
        flash("Unauthorized access.", "danger")
        return redirect(url_for("home"))

    if request.method == "POST":
        symbol = request.form["symbol"]
        price = float(request.form["price"])
        new_stock = Stock(symbol=symbol, price=price)
        db.session.add(new_stock)
        db.session.commit()
        flash("Stock created successfully!", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("create_stock.html")


@app.route("/admin/change-market", methods=["GET", "POST"])
@login_required
def change_market():
    if current_user.role != "admin":
        flash("Unauthorized access.", "danger")
        return redirect(url_for("home"))
    return render_template("change_market.html")


if __name__ == "__main__":
    app.run(debug=True)
