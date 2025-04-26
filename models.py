from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    _tablename_ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    trust_score = db.Column(db.Float, default=5.0)
    skillcoins_balance = db.Column(db.Float, default=0.0)

    skills = db.relationship('Skill', backref='user', lazy=True)
    transactions_given = db.relationship('Transaction', foreign_keys='Transaction.offerer_id', backref='offerer', lazy=True)
    transactions_received = db.relationship('Transaction', foreign_keys='Transaction.requester_id', backref='requester', lazy=True)

class Skill(db.Model):
    _tablename_ = 'skill'

    id = db.Column(db.Integer, primary_key=True)
    skill_name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_offered = db.Column(db.Boolean, default=True)
    availability = db.Column(db.String(100))

class Transaction(db.Model):
    _tablename_ = 'transaction'

    id = db.Column(db.Integer, primary_key=True)
    offerer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    skill_id = db.Column(db.Integer, db.ForeignKey('skill.id'), nullable=False)
    amount_paid = db.Column(db.Float)
    transaction_date = db.Column(db.DateTime, default=db.func.current_timestamp())

class TrustScore(db.Model):
    _tablename_ = 'trust_score'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    trust_score = db.Column(db.Float, default=5.0)
